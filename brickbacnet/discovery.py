"""
    DISCOVERY.PY
    Script to discover backnet devices and save the received data into json files.
    Built using bacpypes
"""


import logging
import time
import threading
import json
import configparser

from pdb import set_trace as bp

from bacpypes.core import run
from bacpypes.pdu import Address
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.iocb import IOCB
from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest, ReadPropertyACK
from bacpypes.local.device import LocalDeviceObject
from bacpypes.app import BIPSimpleApplication
from bacpypes.primitivedata import Unsigned, ObjectIdentifier
from bacpypes.object import get_datatype
from bacpypes.constructeddata import Array
from bacpypes.task import TaskManager

from .common import make_src_id
from .sqlite_wrapper import SqliteWrapper


class BacnetDiscovery(BIPSimpleApplication):
    def __init__(
        self, bacpypes_inifile, brickbacnet_config, sqlite_db,
    ):
        self.logger = logging.getLogger('bacnet_discovery')
        self.logger.setLevel(logging.WARNING)
        config = configparser.ConfigParser()
        config.read(bacpypes_inifile)
        config = config["BACpypes"]
        self.address_mask = config["address"]  # TODO: What does this do?
        self.this_device = LocalDeviceObject(
            objectName=config["objectName"],
            objectIdentifier=int(config["objectIdentifier"]),
            maxApduLengthAccepted=int(config["maxApduLengthAccepted"]),
            segmentationSupported=config["segmentationSupported"],
            vendorIdentifier=int(config["vendorIdentifier"]),
            vendorName="brick-community",
        )
        self.sqlite_db = sqlite_db

        BIPSimpleApplication.__init__(self, self.this_device, config["address"])
        self.taskman = TaskManager()
        self.object_custom_fields = brickbacnet_config['object_custom_fields']

    def indication(self, apdu):
        """ function called as indication that an apdu was received """

        if isinstance(apdu, IAmRequest):
            dev_data = {}
            dev_data["addr"] = str(apdu.pduSource)
            dev_data["device_id"] = repr(apdu.iAmDeviceIdentifier[1])  # just the number
            dev_data["device_identifier"] = ":".join(
                [str(x) for x in apdu.iAmDeviceIdentifier]
            )
            dev_data["max_apdu"] = str(apdu.maxAPDULengthAccepted)
            dev_data["segmentationSupported"] = str(apdu.segmentationSupported)
            dev_data["vendor_id"] = str(apdu.vendorID)
            self.devices[apdu.iAmDeviceIdentifier[1]] = dev_data

        BIPSimpleApplication.indication(self, apdu)

    def do_read(self, addr, obj_id, prop_id, indx=None):
        """ do_read( <address to read from>, <object_id>, <property_id>, <optinal index>)
            read a property from a specific object.
            if read fails return None.
        """
        try:
            obj_id = ObjectIdentifier(obj_id).value

            datatype = get_datatype(obj_id[0], prop_id)
            if not datatype:
                self.logger.info("%s: invalid property for object type" % prop_id)
                return None

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=obj_id, propertyIdentifier=prop_id,
            )
            request.pduDestination = Address(addr)

            if indx is not None:
                request.propertyArrayIndex = indx

            iocb = IOCB(request)
            self.request_io(iocb)
            # time.sleep(3)

            iocb.set_timeout(5)
            iocb.wait()

            if iocb.ioError:
                self.logger.error("READ ERROR:" + str(iocb.ioError) + "\n")

            elif iocb.ioResponse:
                apdu = iocb.ioResponse
                if not isinstance(
                    apdu, ReadPropertyACK
                ):  # should be an ack to our request
                    self.logger.error("Response not an ACK")
                    return None

                datatype = get_datatype(
                    apdu.objectIdentifier[0], apdu.propertyIdentifier
                )
                if not datatype:
                    self.logger.info("unknown datatype")
                    return None

                # special case for array parts, others are managed by cast_out
                if issubclass(datatype, Array) and (
                    apdu.propertyArrayIndex is not None
                ):
                    if apdu.propertyArrayIndex == 0:
                        value = apdu.propertyValue.cast_out(Unsigned)
                    else:
                        value = apdu.propertyValue.cast_out(datatype.subtype)
                else:
                    value = apdu.propertyValue.cast_out(datatype)
                return value

            else:
                self.logger.error("ioError or ioResponse expected")
        except Exception as error:
            self.logger.error("exception:", error)

        return None

    def discover_devices(self, timeout=5):
        """ Send a WhoIsRequest and wait for timeout seconds to receive all responses.  """
        self.devices = {}
        req = WhoIsRequest() # How does this know it needs to store at devices?
        req.pduDestination = Address("255.255.255.255")  # Global Broadcast address

        iocb = IOCB(req)
        self.request_io(iocb)
        iocb.set_timeout(5)
        iocb.wait()
        time.sleep(timeout)  # wait for 5 seconds so all the responses are received.

        self.update_device_metadata(self.devices)
        return self.devices

    def update_device_metadata(self, devices):
        for dev in devices.values():
            dev["name"] = self.do_read(
                dev["addr"], dev["device_identifier"], "objectName",
            )
            dev["description"] = self.do_read(
                dev["addr"], dev["device_identifier"], "description",
            )
            dev["obj_count"] = self.do_read(
                dev["addr"], dev["device_identifier"], "objectList", 0
            )
            dev["jci_name"] = self.do_read(
                dev["addr"], dev["device_identifier"], "jci_name", 0
            )

            self.sqlite_db.write_device_properties(dev)

    def discover_objects(self, target_devices):
        """ input_device_id_list specifies the objects to collect data from.
            if input_device_id_list is empty, data is collected from all devices discovered by whois
        """
        device_objs = {}
        for device_id, dev in target_devices.items():
            objs = {}
            if not dev["obj_count"]:
                self.logger.warning(f'Device {device_id} does not have any objects.')
                continue
            # read properties of the objects
            for obj_idx in range(1, int(dev["obj_count"]) + 1)[0:10]: #TODO: Remove this
                time.sleep(0.05) # TODO: Configure this.
                obj = self.do_read(
                    dev["addr"], dev["device_identifier"], "objectList", obj_idx
                )
                if obj is None:
                    self.logger.warning(f"Object {obj_idx} in Device {device_id} does not exist.")
                    continue
                obj_id = ":".join([str(x) for x in obj])
                if obj_id in objs:
                    self.logger.warning(f"Object {obj_id} already exists in Device {device_id}.")
                obj_res = {
                    "index": obj_idx,
                    "device_id": device_id,
                    "instance": obj[1],
                    "object_identifier": ":".join([str(x) for x in obj]),
                    "object_type": self.do_read(dev["addr"], obj, "objectType"),
                    "description": self.do_read(dev["addr"], obj, "description"),
                    "jci_name":    self.do_read(dev["addr"], obj, "jciName"),
                    "sensor_type": self.do_read(dev["addr"], obj, "deviceType"),
                    "unit": self.do_read(dev["addr"], obj, "units"),
                    "source_identifier": make_src_id(device_id, obj_id),
                }
                obj_res["uuid"] = None

                for field, prop in self.object_custom_fields.items():
                    obj_res[field] = self.do_read(dev['addr'], obj, prop)

                self.sqlite_db.write_obj_properties(obj_res)

                objs[obj_id] = obj_res
            device_objs[device_id] = objs
        return device_objs


def run_thread():
    """ bacpypes runs a async core, which processes incoming responses, before handing over to
        the concerned iocb as either an ioResponse or as an ioError.
    """
    run()  # blocked
