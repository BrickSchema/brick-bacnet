import os
import logging
from logging.handlers import RotatingFileHandler
import time
import json
from operator import itemgetter
from concurrent import futures
from datetime import datetime
from pdb import set_trace as bp

#import grpc

from .bacnet_wrapper import  BacnetWrapper
#from .actuation_server import ActuationServer
from .common import make_src_id, make_obj_id, striding_window
from .brickserver import BrickServer
from .sqlite_wrapper import SqliteWrapper


def create_logger(logfile):
    logger = logging.getLogger(logfile)
    logger.setLevel(logging.INFO)
    fh = RotatingFileHandler(logfile, mode='a', maxBytes=5*1024*1024,
                                     backupCount=1, encoding=None, delay=0)
    fh.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(log_formatter)
    logger.addHandler(fh)
    return logger


class Connector(object):
    def __init__(self,
                 bacpypes_ini,
                 ds_if,
                 clear_cache=False,
                 config={},
                 ):
        #Initialize logging
        self.logfile = config['connector'].get('logfile')
        self.logger = create_logger(self.logfile)
        self.min_interval = config['connector'].get("min_interval", 120)
        self.read_sleeptime = config['connector'].get("read_sleeptime", 0.05)
        self.rpc_workers = config['connector'].get("num_rpc_workers", 10)
        self.read_batch_size = config['connector'].get('read_batch_size', 20)
        self.btype_dtype_map = {
        } # BAcnet type to data type map.

        self.bacnet = BacnetWrapper(bacpypes_ini)
        self.ds_if = ds_if

        self.logger.info("Initialized BACnet")
        self.bacnet_dev_ids = config['target_bacnet_devices']
        self.sqlite_db = SqliteWrapper(config['sqlite_db'])
        # read device data from the SQLite database. Updates to device data can be handled without
        # restarting connector.


    def read_all_devices_forever(self):
        for dev_id in self.bacnet_dev_ids:
            prev_time = time.time()
            self.read_device_once(dev_id)
            curr_time = time.time()
            delta_time = curr_time - prev_time
            if delta_time < self.min_interval:
                print('wait: {0}'.format(self.min_interval - delta_time))
                time.sleep(self.min_interval - delta_time)

    def read_object(self, dev, obj_type, obj_instance, obj_property='presentValue'):
        value = self.bacnet.do_read(dev['addr'], obj_type, obj_instance, prop_id=obj_property)
        timestamp = time.time()
        return {
            'timestamp': timestamp,
            'value': value,
        }

    def get_uuid(self, dev_ref, obj_instance):
        uuid = self.sqlite_db.find_obj_uuid(def_ref, obj_instance)
        return uuid

    def read_device_once(self, dev_id):
        dev = self.sqlite_db.read_device_properties(dev_id)
        object_ids = dev["objects"]
        for window_obj_ids in striding_window(object_ids, self.read_batch_size):
            datapoints = []
            for obj_instance in window_obj_ids:
                obj = self.sqlite_db.read_obj_properties(device_id=dev_id, instance=obj_instance)
                try:
                    datapoint = self.read_object(dev, obj['object_type'], obj_instance)
                except Exception as e:
                    if str(e).split(':')[-1] == 'invalid property for object type':
                        self.logger.warning('Object {0} at Device {1} is not read because "{2}"'.format(
                            obj['isntance'], dev_id, e
                        ))
                        datapoint = None
                    else:
                        raise e
                uuid = self.sqlite_db.find_obj_uuid(dev_id, obj_instance)
                assert uuid, 'UUID not found for the object {0} in device {1}'.format(obj_instance, dev_id)
                datapoint['uuid'] = uuid
                datapoint['object_type'] = obj['object_type']
                datapoints.append(datapoint)
                time.sleep(self.read_sleeptime)
            self.ds_if.put_timeseries_data(datapoints) # TODO: Make this async later.

    def read_device_forever(self, dev_id):
        while True:
            prev_time = time.time()
            self.read_device_once(dev_id)
            curr_time = time.time()
            delta_time = curr_time - prev_time
            if delta_time < self.min_interval:
                print('wait: {0}'.format(self.min_interval - delta_time))
                time.sleep(self.min_interval - delta_time)

    def start_rpc_server(self):
        rpc_server = grpc.server(futures.ThreadPoolExecutor(self.rpc_workers))
        dsrpc_mtd.add_DataserviceServicer_to_server(ActuationServer(), rpc_server)
        rpc_server.add_insecure_port('[::]:70000')
        rpc_server.start()
