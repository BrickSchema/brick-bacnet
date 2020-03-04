BACnet2Brick
------------
A virtual BACnet device that can connect BACnet to Brick Server.

# Features
- Discovery of bacnet devices and objects.
- Registeration of the identified devices and objecst to a Brick Server.
- Periodic publication of the data to Brick Server.
- A gRPC server that can receive actuation request, which is delivered to actual BACnet devices.

# Installation
- TODO for Python
- (Optional): Install Brick Server. This is necessary if you want to communicate with a Brick Server.
- You need to have a machine (raspberry pi, a VM, or any Linux hosting machine) that have accessibility of both BACnet devices (BACnet/IP) and your Brick Server (e.g., the Internet).

# How to use it?
- `b2b --help` to list available commands.
    - `b2b discovery --help` to get help for discovery
    - `b2b connector --help` to get help for the connector
- Configuration: Update `configs/b2b_config.json.template`.
- `b2b discovery`: This discovers all the BACnet devices and objects and store them in a sqlite db.
- `b2b connector`: This periodically polls all the points and push them to a Brick Server. When activated, it can receive actuation requests as well.

# Example Commands
- `./b2b discovery --target-devices 123,124 --registerbrick-server`: Discover all objects from BACnet devices, 123 and 125 and register them at a designated Brick Server
- `./b2b connector --target-devices 123,124`: Periodically update the objects' data in the BACnet devices 123 and 124 to the Brick Server.


# Tutorial
1. Make sure your hosting machine has the connection to both BACnet devices and a Brcik Server.
2. Create `configs/b2b_config.json` based on `configs/b2b_config.json.template`.
3. Run `b2b discovery --register-brickserver`` to automatically register all the discovered devices and objects in to the Brick Server.
4. Run `b2b connector` to periodically push all the data to the Brick Server.
    - Use ``--receive-actuation``


# The current security issues
- Currently actuation has no auth mechanism. One should carefully activate it like behind proper `iptables` rules.

