BACnet2Brick
------------
A virtual BACnet device that can connect BACnet to Brick Server.

# Features
- Discovery of bacnet devices and objects.
- Registeration of the identified devices and objecst to a Brick Server.
- Periodic publication of the data to Brick Server.
- A gRPC server that can receive actuation request, which is delivered to actual BACnet devices. (under development)

# Requirements
- This code has been tested on Ubuntu. It may work for other OSes without guarantee.
- This tool assumes BACnet/IP protocol though it can potentially work with BACnet/MSTP. Please let the maintainers know if you need to use this for BACnet/MSTP.
- You need a machine that can communicate with the BACnet devices in the BACnet network. It's oftens implemented as a subnet.
    - If you need to continously post the data to an endpoint like Brick Server, your machine should be able to reach the endpoint as well.

# Installation
## Install necessary packages
1. `python3 -m venv env`
2. `source env/bin/activate`
3. `pip install -r requirements.txt`

## Update BACpypes for custom fields.
Your BACnet devices might have a custom ObjectProperty such as `JCI_NAME`. If you want to retrieve them, you have to add the information inside the `bacpypes` package as well.
### Example
Apply patch `configs/BACKPYPES_JCI.patch` to the installed bacpypes package. (usually at `<env path>/lib/python3.6/site-packages/bacpypes`. This lets the script read `JCI_NAME` property.

## (Optional): Install Brick Server.
1. This is only necessary if you want to communicate with a Brick Server.
2. You need to have a machine (raspberry pi, a VM, or any Linux hosting machine) that have accessibility of both BACnet devices (BACnet/IP) and your Brick Server (e.g., the Internet).

# Getting Started
## Configure BACpypes.ini
1. Create `configs/BACpypes.ini` based on `configs/BACpypes~.ini`.
2. Change the parameters. Refer to https://github.com/JoelBender/bacpypes for more details.

## Configure Brick2BACnet
1. Create `configs/b2b_config.json` based on `configs/b2b_config.json.template`.
2. Change the parameters.
    - `object_custom_fields` refers to the custom fields you manually added above.
3. (Optional) If you need to post the results into a Brick Server, please refer to https://github.com/brickschema/brick-server to spin up one.
    1. You can get a `jwt_token` from your Brick Server.


# How to use it?
- `b2b --help` to list available commands.
    - `b2b discovery --help` to get help for discovery
    - `b2b connector --help` to get help for the connector
- `b2b discovery`: This discovers all the BACnet devices and objects and store them in a sqlite db.
- `b2b connector`: This periodically polls all the points and push them to a Brick Server. When activated, it can receive actuation requests as well.

# Example Commands
- `./b2b discovery --target-devices 123,124 --registerbrick-server`: Discover all objects from BACnet devices, 123 and 125 and register them at a designated Brick Server
- `./b2b connector --target-devices 123,124`: Periodically update the objects' data in the BACnet devices 123 and 124 to the Brick Server.
    - Use ``--receive-actuation`` to activate actuation (under dev)


# Tutorial
1. Make sure your hosting machine has the connection to both BACnet devices and a Brcik Server.
2. Create `configs/b2b_config.json` based on `configs/b2b_config.json.template`.
3. Run `b2b discovery --register-brickserver`` to automatically register all the discovered devices and objects in to the Brick Server.
4. Run `b2b connector` to periodically push all the data to the Brick Server.


## Additional References:
1. OpenAgricultureFoundation's [bacnet wrapper](https://github.com/OpenAgricultureFoundation/openag-device-software/blob/830011c0669eb7dbfc3361dafbfa065ba6a6a98f/device/peripherals/modules/bacnet/bnet_wrapper.py)
2. ReadProperty.py and WhoIsIAm.py in bacpypes [samples](https://github.com/JoelBender/bacpypes/tree/master/samples)
