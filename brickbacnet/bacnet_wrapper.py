"""
    BACNET_WRAPPER.PY
    A wrapper over bacpypes, to read and write sensor data.
    Sensor address is read from a config file.
"""

from pdb import set_trace as bp

import threading
from bacpypes.core import run
from bacpypes.pdu import Address
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.iocb import IOCB
from bacpypes.apdu import ReadPropertyRequest, \
                          ReadPropertyACK, WritePropertyRequest, SimpleAckPDU
from bacpypes.constructeddata import Array, Any, AnyAtomic
from bacpypes.primitivedata import Null, Atomic, Boolean, Unsigned, Integer, \
    Real, Double, OctetString, CharacterString, BitString, Date, Time, ObjectIdentifier, Enumerated
from bacpypes.primitivedata import ObjectType
from bacpypes.local.device import LocalDeviceObject
from bacpypes.app import BIPSimpleApplication
from bacpypes.object import get_datatype
from bacpypes.task import TaskManager
from bacpypes.pdu import Address

from .common import make_obj_id

def get_port_from_ini(ini_file):
    args = ConfigArgumentParser().parse_args(["--ini", ini_file])
    addr = Address(args.ini.address)
    return addr.addrPort

def get_static_object_types():
    obj_types = ObjectType.enumerations.keys()
    non_dynamic_objects = [obj_type for obj_type in obj_types
                           if not get_datatype(obj_type, 'presentValue')]
    return non_dynamic_objects


class BacnetWrapper(BIPSimpleApplication):
    """ The class that wraps over the underlying bacnet library (bacpypes).
        Provide simple read and write functions.
    """

    def __init__(self, ini_file, overriding_port: int=None):
        self.args = ConfigArgumentParser().parse_args(["--ini", ini_file])
        #addr = Address(self.args.ini.address)
        #if overriding_port:
        #    addr.addrPort = overriding_port
        #print('Address: {0}'.format(addr.addrPort))
        if overriding_port:
            ip, port = self.args.ini['address'].split(':')
            self.args.ini['address'] = ip + ':' + str(overriding_port)
        self.this_device = LocalDeviceObject(ini=self.args.ini)
        BIPSimpleApplication.__init__(self, self.this_device, self.args.ini['address'])
        self.taskman = TaskManager()
        self.datatype_map = {
                'b': Boolean,
                'u': lambda x: Unsigned(int(x)),
                'i': lambda x: Integer(int(x)),
                'r': lambda x: Real(float(x)),
                'd': lambda x: Double(float(x)),
                'o': OctetString,
                'c': CharacterString,
                'bs': BitString,
                'date': Date,
                'time': Time,
                'id': ObjectIdentifier,
                }

        thread_handle = threading.Thread(target=self.run_thread)
        thread_handle.daemon = True
        thread_handle.start()

    def run_thread(self):
        """ bacpypes runs a async core, which processes incoming responses, before handing over to
            the concerned iocb as either an ioResponse or as an ioError.
        """
        run() # blocked

    def do_read(self,
                dev_addr: str,
                obj_type: str,
                obj_instance: int,
                prop_id: str,
                indx: int=None,
                ):
        """ read a property of a specific object from a device at `dev_addr`.
            if read fails, raise exception
        """
        obj_id = make_obj_id(obj_type, obj_instance)
        obj_id = ObjectIdentifier(obj_id).value
        datatype = get_datatype(obj_id[0], prop_id)
        if not datatype:
            raise Exception(f"{prop_id}:invalid property for object type '{obj_type}'")

        # build a request
        request = ReadPropertyRequest(
            objectIdentifier=obj_id,
            propertyIdentifier=prop_id,
            )
        request.pduDestination = Address(dev_addr)

        if indx is not None:
            request.propertyArrayIndex = indx

        iocb = IOCB(request)
        self.request_io(iocb)

        iocb.set_timeout(3)
        iocb.wait()

        if iocb.ioError:
            raise Exception("READ ERROR:" + str(iocb.ioError))

        if iocb.ioResponse:
            apdu = iocb.ioResponse
            #print("read resp %s"%apdu)
            if not isinstance(apdu, ReadPropertyACK): #should be an ack to our request
                raise Exception("Response not an ACK")

            datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
            if not datatype:
                raise Exception("unknown datatype")

            # special case for array parts, others are managed by cast_out
            if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.cast_out(Unsigned)
                else:
                    value = apdu.propertyValue.cast_out(datatype.subtype)
            else:
                value = apdu.propertyValue.cast_out(datatype)

            if type(value) in [Enumerated, Unsigned]:
                return value.__dict__["value"]

            return value

        else:
            raise Exception("ioError or ioResponse expected")


    def do_write(self, device_id, object_type, object_instance, prop_id, value, \
                 prop_type='invalid prop_type', indx=None, priority=None):
        """ do_write( <object id>, <type>, <instance>, <property_id>, <value>,
                      <optional property type>, <optional index>, <optional priority> )
            write a property to a specific object.
            return Nothing if successful, else Raise an exception which can be logged.
        """
        addrlist = device_id["mac"] #4 bytes of address, 2 bytes of port
        if len(addrlist) != 6:
            raise IOError('invalid address')
        addr = ".".join(str(x) for x in addrlist[:4])  + ":" + str((addrlist[4]<<8) + addrlist[5])

        obj_id = str(object_type) + ":" + str(object_instance)
        obj_id = ObjectIdentifier(obj_id).value
        datatype = get_datatype(obj_id[0], prop_id)

        # change atomic values into something encodeable, null is a special case
        if value == 'null':
            value = Null()
        elif issubclass(datatype, AnyAtomic):
            datatype = self.datatype_map[prop_type]
            value = datatype(value) # based on prop type build a value

        elif issubclass(datatype, Atomic):
            if datatype is Integer:
                value = int(value)
            elif datatype is Real:
                value = float(value)
            elif datatype is Unsigned:
                value = int(value)
            value = datatype(value)

        elif issubclass(datatype, Array):
            if indx is None:
                raise Exception("Index field missing")
            if indx == 0:
                value = Integer(value)
            elif issubclass(datatype.subtype, Atomic):
                value = datatype.subtype(value)
            elif not isinstance(value, datatype.subtype):
                raise TypeError("invalid result datatype, expecting %s" % (datatype.subtype.__name__,))
        elif not isinstance(value, datatype):
            raise TypeError("invalid result datatype, expecting %s" % (datatype.__name__,))

        # build request & save the value
        request = WritePropertyRequest(
            objectIdentifier=obj_id,
            propertyIdentifier=prop_id
            )
        request.pduDestination = Address(addr)

        request.propertyValue = Any()
        request.propertyValue.cast_in(value)

        if indx is not None:
            request.propertyArrayIndex = indx

        if priority is not None:
            request.priority = priority

        # make an IOCB
        iocb = IOCB(request)
        self.request_io(iocb)
        iocb.set_timeout(3)
        iocb.wait()

        if iocb.ioResponse:
            if not isinstance(iocb.ioResponse, SimpleAckPDU):
                raise Exception("Response Not an ACK")

            return # write success

        if iocb.ioError:
            raise Exception("ioError: %s"+str(iocb.ioError))

        raise Exception("do_write failed")
