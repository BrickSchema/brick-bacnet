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

#class BDSensorObj(DsSensorObj):
#    """ The sensor object. contains the UUID and sensorpoint type """
#    uuid = None
#    sensorpoint_type = None
#    def __init__(self,
#                 uuid,
#                 sensorpoint_type):
#        self.uuid = uuid
#        self.sensorpoint_type = sensorpoint_type

# Coding Convention: (this is followed unless specified)
# obj: BACnet Object
# dev: BACnet Device (e.g., NAE)


class Connector(object):
    def __init__(self,
                 bacpypes_ini,
                 ds_if,
                 clear_cache=False,
                 config={},
                 ):
        #Initialize logging
        self.logfile = config.get('logfile')
        self.logger = create_logger(self.logfile)
        self.min_interval = config.get("min_interval", 120)
        self.read_sleeptime = config.get("read_sleeptime", 0.05)
        self.rpc_workers = config.get("num_rpc_workers", 10)
        self.read_batch_size = config.get('read_batch_size', 20)
        self.btype_dtype_map = {
        } # BAcnet type to data type map.

        self.bacnet = BacnetWrapper(bacpypes_ini)
        self.ds_if = ds_if

        self.logger.info("Initialized BACnet")

        if clear_cache:
            os.remove("sensor_uuid.json")

        bacnet_dev_ids = config['bacnet_dev_ids']
        self.bacnet_dev_objs = {}

        #for dev_id in bacnet_dev_ids:
        #    uuid_file = 'results/{0}_uuids.json'.format(dev_id)
        tot_dev_objs = json.load(open('results/bacnet_objects.json'))
        self.bacnet_dev_objs = {dev_id: tot_dev_objs[dev_id] for dev_id in bacnet_dev_ids}


        tot_devs = json.load(open('results/bacnet_devices.json'))
        self.bacnet_devs= {dev_id: tot_devs[dev_id] for dev_id in bacnet_dev_ids}



    def read_all_devices_forever(self):
        for dev_id in self.bacnet_devs.keys():
            self.read_device_forever(dev_id)


    def read_object(self, dev, obj_type, obj_instance, obj_property='presentValue'):
        value = self.bacnet.do_read(dev['addr'], obj_type, obj_instance, prop_id=obj_property)
        timestamp = time.time()
        return {
            'timestamp': timestamp,
            'value': value,
        }

    def read_device_once(self, dev_id):
        dev = self.bacnet_devs[dev_id]
        objs = self.bacnet_dev_objs[dev_id]
        for window_objs in striding_window(list(objs.values()), self.read_batch_size):
            datapoints = []
            for obj in window_objs:
                try:
                    datapoint = self.read_object(dev, obj['object_type'], obj['instance'])
                    datapoint['src_id'] = make_src_id(dev_id, make_obj_id(obj['object_type'], obj['instance']))
                except Exception as e:
                    if str(e).split(':')[-1] == 'invalid property for object type':
                        logger.warning('Object {0} at Device {1} is not read because "{2}"'.format(
                            obj['isntance'], dev_id, e
                        ))
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
