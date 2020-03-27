# udrone - QA can be done right

- What is udrone
- Definition of test cases
- Using iterations and substitution
- List of all complex calls
- List of all drone calls

## What is udrone

Udrone is a system that allows you to remotely control *N* drones. The *N*
drones can be sent a number of different commands. Based on these commands the
drone will perform a number of actions and report the result back to the drone
host controller. The system consists of a number of files on the controller
side.

- `udrone.py` - the core component. This code establishes a communication channel to the drone.
- `qa.py` - this is a wrapper for udrone.py that allows us to write test in json syntax and run them in a sane manner
- `*.json` - this is a collection of predefined tests, that the drone can run

## Setup Guide

* Where do I get udrone
* How do I setup udrone software
* How do I setup udrone hardware
* How do I run a test

### Where do I get udrone

Checkout the latest version via the following command

```
git clone https://github.com/blogic/udrone
```

### How do I setup udrone software

udrone is very easy to setup. All custom information is stored in a central
file called conf.py

```
$ cat conf.py
conf = {
    # the interface used to talk to the drones
    ifname":"eth0",
}
```

### How do I setup udrone hardware

In addition to the DUT you will need N drones. A drone is a OpenWrt router with
the udrone package installed. Once you have all devices, you need to set them
up in 1 of the following ways.

```
LAPTOP (eth0) -> (LAN) DRONE (WAN) -> (LAN) DUT (WAN) -> BACKEND
LAPTOP (eth0) -> (LAN) DRONE (WIFI) -> (WIFI) DUT (WAN) -> BACKEND
```

If you want to use more than just 1 Drone you will need to switches between
LAPTOP/DRONE and DRONE/DUT.

As a backend you will need, depending on the test: AP/PPPoE Server/DHCP/DNS/...

## How do I run a test

The simplest test is the connectivity test. This will make the drone grab an
IPV4 using DHCP from the DUT and wget http://openwrt.org/index.html.

```
$ ./qa.py test/example.connectivity.json
```

Once all test are run, the qa tool will report back if the test passed or
failed.

## Definition of test cases

So, lets start by looking at the format of the json file. The basic layout of
any json based test description is as follows

```
{
    "id":"The ID of the test",
    "desc":"The description of the test",
    "drones":the_number_of_drones,
    "test":[ the actual test case go here ],
}
```

Within the test:[] entity we will start to define all the different test cases
that want to run as part of this test. A typical testcase would look like this

```
{
    "desc":"use fatserver calls to set public_essid)",
    "repeat":how_often_we_want_to_run_the_test,
    "first":loop_from_first,
    "last":loop_to_last,
    "sleep":how_many_seconds_to_sleep_after_the_test,
    "cmd":[ the actual commands to be called go here ],
}
```

If last/first is set, repeat will be ignored.

Within the cmd:[] entity we define the actual real commands that we want the
drone to execute as part of the test. Consider these to be a reduced to the
smallest denominator of commands called (or in other terms, these are risc
commands and not cisc). The command can have a verity of functions, from
setting local and remote network settings, doing a generic sleep, talking to
the DUT, doing random networkery, ...

Lets start by looking at a single row

```
[ "ACTION", .................. ]
```

Every line start with a ACTION. Depending on the real ACTION to take, we can
have N parameters following the ACTON call.

Actions can be of 3 types. So lets look at 3 lines

```
{
    [ "sleep", 5 ],
    [ "drone", 1, "webui_auth", {"pass":"foobar"}, 300 ],
    [ "essid", 1, "foorandom", "12345321234" ],
}
```


- sleep - sleep

```
    # this makes the system wait 5 seconds
    [ "sleep", 5 ]
```

- drone - send commands to drone

----
```
    # we want to send a command to a drone, whose id is 1, the commands id is
    # "webui_auth" and we pass the payload {"pass":"foobar"}. if the call fails
    # to return within 300s, we raise a failure/exception
    [ "drone", 1, "webui_auth", {"pass":"foobar"}, 300 ],

```

* $complex - when ACTIONS become to complex to be handled by the "drone" call,
  we can add additional handlers inside qa.py to abstract the complexion away
  abit.

```
    # run the complex command essid. this sets the essid of drone 1 to
    # foorandom and uses 12345321234 as a passphrase this call is complex as we
    # don't only send a command, but 2 and then poll for their completion.
    # Completion is detected by polling the network status reporting info from
    # the DUT
    [ "essid", 1, "foorandom", "12345321234" ]
```

All complex functions are located inside qa.py

A full test would look like this:

```
{
    "id":"test123",
    "desc":"A demo testcase.",
    "drones":1,
    "test":
    [
        {
            "desc":"log into webui and set essid",
            "repeat":1,
            "sleep":1,
            "cmd":
            [
                {
                    [ "sleep", 5 ],
                    [ "drone", 1, "webui_auth", {"pass":"foobar"}, 300 ],
                    [ "essid", 1, "foorandom", "12345321234" ],
                }
            ],
        },
    ],
}
```


## Using iterations and substitution

As described above a test set can be repeated N times (repeat: 4). To reflect
the N iterations within the test we can use variable substitution. To do so,
simply place `$iterate` inside any parameter section and it will get magically
replaced by the backend. A simple iteration example would look like this.

```
{
    "id":"example.iterate",
    "desc":"Demo of how iterate works",
    "drones":1,
    "test":[
        {"desc":"repeat example",
        "repeat":4,
        "sleep":2,
        "cmd":[ [ "comment", "Iteration $iterate" ] ]
        }
    ]
}


-->
RUN "iterate" - iteration 1
COMMENT Iteration 1
RUN "iterate" - iteration 2
COMMENT Iteration 2
RUN "iterate" - iteration 3
COMMENT Iteration 3
RUN "iterate" - iteration 4
COMMENT Iteration 4

{
    "id":"example.iterate",
    "desc":"Demo of how iterate works",
    "drones":1,
    "test":[
        {"desc":"first->last example",
        "first":4,
        "last":"6,
        "sleep":2,
        "cmd":[ [ "comment", "Iteration $iterate" ] ]
        }
    ]
}

-->
RUN "iterate" - iteration 4
COMMENT Iteration 4
RUN "iterate" - iteration 5
COMMENT Iteration 5
RUN "iterate" - iteration 6
COMMENT Iteration 6
```

In addition we can use variable substation. To do so simply create a new value
inside conf.py and then reference it inside your json code

```
[ "drone", 1, "cloudlogin", {"user":"$cloud_user", "pass":"$cloud_pass", "host":"$cloud_url"}, 300 ]
```

## List of all complex calls

Generally we use complex calls whenever we need to not just send data but wait
for a status.

```
# set a static IP on drone 1
[ "static", 1, "192.168.10.2", "255.255.255.0" ]

# set essid of drone 1 to wifitest and wpa key to foobar
[ "essid", 1, "wifitest", "foobar" ]

# trigger drone 1
[ "dhcp", 1 ]

# sleep 5 seconds
[ "sleep", 1 ]

# fail is a test result inverter. it switces a result true<->false
[ "fail", "dhcp", 1 ]

# this will trigger qa.py to print a comment in the log
[ "comment", "foooooobar" ]

# this will cause drone 1 to try and ping a remote url
[ "ping", 1, "192.168.10.1" ]

# this will check if the IP received in a dhcp reply received by drone 1
# matches certain criterions.
[ "checkip", 1, "192.168.10." ]
```

As netmasks are limited to 32 and or not always obvious which once are valid,
we have 2 special complex calls to handle this. Netmasks are always indexed by
an id rather than a absolute mask.

```
# this will set the netmask on drone 1 to Mask index #1
[ "setnetmask", 1 ]
# this will check if the netmask received in a dhcp reply received by drone 1
# matches certain criterions of Mask index #1
[ "checknetmask", 1 ]
```

Finally we have a complex call that we use as our entry point for RPC on a Drone

```
# send a drone RPC call to drone 1.
[ "drone", 1, "webui_auth", {"pass":"admin"}, 300 ],
```

## List of all drone calls

```
# dns_flood - do mass dns resolving
[ "drone", 1, "dns_flood", ["www.google.de", "www.google.com"]

# download - download a file and check its size
[ "drone", 1, "download", {"url":"http://dev.phrozen.org/test", "repeat":"4", "size":"1048576"}, 300 ]

# fatserver - simulate a fatserver call - this requires a DUT with dev mode enabled
[ "drone", 1, "fatserver", {"host":"192.168.10.1", "payload":"json|{\"cmd\":\"setwpapassword\", \"val\":\"12345321234\" }" } ]

# cloudlogin - log into a cloudspot using http redirects
[ "drone", 1, "cloudlogin", {"user":"$cloud_user", "pass":"$cloud_pass", "host":"$cloud_url"}, 300 ]

# cloudwispr - log into a cloudspot using wispr

# cloudlogout - log of the cloud service
[ "drone", 1, "cloudlogout" ]

# webui_auth - tell the drone to log into the DUTs webui
[ "drone", 1, "webui_auth", {"pass":"admin"}, 300 ]

# webui_rpc - send a webui rpc call (these are identical to the ones used by the normal webui)
[ "drone", 1, "webui_rpc", { "set":"passwd", "vals":{"passwd1":"fooooooooo" } } ],

# webui_deauth - log off the webui
[ "drone", 1, "webui_deauth" ]

# webui_ip - use a different webui ip than 192.168.10.1
[ "drone", 1, "webui_ip", {"ipaddr":"169.254.255.1"}, 300 ],

# uci_dump - get
[ "drone", 1, "uci_dump", {"package":"cloud", "section":"state", "state":1 }, 300 ],
```


The following calls exist but are currently unused

- upgrade - FW upgrade of the Drone
- system - execute a random system call on the drone
- uci_dump - get some use values
- uci_replace - uci magic
- getifaddrs - get a list of all netdevs inclusive the ipaddr ...
- reset - reboot the drone
- readfile - read a random file from the drones FS
- sysinfo - get system resource usage
