# Testing calls

To test the client side of `udrone` it is possible to run a snippet which sends
a command to drones. Find the snippet at the bottom of this page.

The snippet does not require `udronerc` to be installed nor any packages
outside Pythons standard library.

Follow the [test-setup] instructions to have a Docker container locally running.

The snippet syntax is as follows:

    ./snippet.py <local_ip> <cmd> <data>

The `local_ip` must be the one attached to your Docker bridge.

A working command for a Docker container running in default network `192.168.1.1` is the following:

    ./snippet.py 192.168.1.2 sysinfo '{}'
    ./snippet.py 192.168.1.2 ubus '{ "path": "system", "method": "board" }'

The response is simple is formatted JSON.

## Call snippet

```python
import socket
import sys
import os
import struct
import json


if len(sys.argv) != 4:
    print(f"{sys.argv[0]} <local_ip> <cmd> <data>")
    exit(1)

local_ip, cmd, data = sys.argv[1:4]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 0))

sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))

seq = struct.unpack("=I", os.urandom(4))[0] % 2000000000

msg_out = {
    "from": "testhost",
    "to": "!all-default",
    "type": cmd,
    "seq": seq,
    "data": json.loads(data),
}

packet = json.dumps(msg_out, separators=(",", ":"))
sock.sendto(packet.encode("utf-8"), ("239.6.6.6", 21337))
print(f"Sending {msg_out}")
msg_in = sock.recvmsg(32 * 1024)[0].decode()
print(f"Received {json.loads(msg_in)}")
```
