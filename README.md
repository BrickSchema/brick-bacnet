# discovery.py

script to discover bacnet devices, built using [bacpypes](https://github.com/JoelBender/bacpypes). 

### Instructions:
1. install bacpypes
2. apply patch `BACKPYPES_JCI.patch` to the installed files. (usually at `<env path>/lib/python3.6/site-packages/bacpypes`. This lets the script read JCI_NAME property.
3. Run discovery2.py .  Edit according to needs. By default it finds all objects and properties and writes then to `full_devices.json` and `devices.json`. Make sure `BACpypes.ini` is in the same directory as `disovery2.py`. Else edit `INI_FILE`.
4. Additional examples are provided at the end of the file.

### Additional References:
1. OpenAgricultureFoundation's [bacnet wrapper](https://github.com/OpenAgricultureFoundation/openag-device-software/blob/830011c0669eb7dbfc3361dafbfa065ba6a6a98f/device/peripherals/modules/bacnet/bnet_wrapper.py)
2. ReadProperty.py and WhoIsIAm.py in bacpypes [samples](https://github.com/JoelBender/bacpypes/tree/master/samples)
