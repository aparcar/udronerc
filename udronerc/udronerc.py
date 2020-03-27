import json
import logging
import os
import sys
import time
from pathlib import Path

import yaml

from .dronegroup import DroneGroup
from .dronehost import DroneHost
from .errors import DroneRuntimeError
from .modules.checkip import checkip

with open("config.yml") as c:
    conf = yaml.safe_load(c.read())

logger = logging.getLogger(__name__)


def get_host():
    return DroneHost(conf["address"], hostid=conf["hostid"])


def replace_tags(msg: str, data: dict):
    """Replaces values inside parameters based on conf.py

    Args:
      msg (str): Message containing tags
      data (dict): Mapping for tags
    """
    return msg.format(*data)


def host_sleep(seconds: int = 5):
    """
    Sleep for N seconds

    Args:
        group
        seconds: Seconds to sleep
    """
    logger.info(f"HOST SLEEP {seconds}")
    time.sleep(seconds)


def host_comment(msg: str):
    """
    Print comment inside the log

    Args:
        msg (str): Comment to print in log
    """
    logger.info("HOST COMMENT {msg}")


def host_raw(cmd):
    logger.info(f"HOST SCRIPT {cmd}")
    logger.warning(f"HOST SCRIPT {cmd} - not yet implented")  # TODO


# this command can be prepended to any other command. it simply inverts the result
def cmd_fail(v, c):
    if cmd_map[v[1]] is not None:
        try:
            cmd_map[v[1]](v[1:], c)
        except:
            logger.debug("INVERT we expected this command to fail which it did")
            return 0
        logger.debug("ERROR command was supposed to fail")
        raise ExceptionClass(1000, "command should have failed", "foo")


# this command executes a shell script. if the script returns 0 we assume all is well


cmds_meta = set(["local", "must_fail" "name"])


def uci_set(group: DroneGroup, data: dict, commit: bool = True):
    responses = group.call("uci_set", data)
    for response in responses:
        logger.debug(f"{response}")

    return responses


def service(group: DroneGroup, name: str, action: str):
    responses = group.call(
        "ubus",
        {
            "path": "luci",
            "method": "setInitAction",
            "param": {"name": name, "action": action},
        },
    )

    return responses


def sysinfo(group: DroneGroup):
    responses = group.call("sysinfo")
    return responses


def read_file(group: DroneHost, path, base64=False):
    responses = (
        group.call(
            "ubus",
            {
                "path": "file",
                "method": "read",
                "param": {"path": path, "base64": base64},
            },
        ),
    )
    return responses


# this is the map of all complex call helpers
cmds_drone = {
    "read_file": read_file,
    "checkip": checkip,
    "checknetmask": {},
    "cloudlogin": {},
    "cloudlogout": {},
    "cloudwispr": {},
    "comment": {},
    "dhcp": {},
    "dns_flood": {},
    "download": {},
    "essid": {},
    "fatserver": {},
    "getifaddrs": {},
    "ping": {},
    "readfile": {},
    "setmask": {},
    "sysinfo": sysinfo,
    "system": lambda x: x.call("ubus", {"path": "system", "method": "board"}),
    "ubus": {},
    "service": service,
    "ubus_call": {},
    "uci_dump": {},
    "uci_get": {},
    "uci_replace": {},
    "uci_set": uci_set,
    "upgrade": {},
    "webui_auth": {},
    "webui_ip": {},
    "webui_rpc": {},
}

cmds_host = {
    "host_sleep": host_sleep,
    "host_comment": host_comment,
    "host_raw": host_raw,
}


cmds_drone_set = set(cmds_drone.keys())
cmds_host_set = set(cmds_host.keys())


def run_task(group, task: dict):
    cmd_set = set(task.keys()) & (cmds_drone_set ^ cmds_host_set)
    logger.debug(f"{cmd_set=}")
    if len(cmd_set) > 1:
        logger.error("Only one command per task allowed")
        quit(1)

    if len(cmd_set) != 1:
        logger.error("Command in task missing or unknown")
        quit(1)

    cmd = cmd_set.pop()
    desc = task.get("name", cmd)
    logger.info(f"Running task {desc}")
    results = []
    if cmd.startswith("host"):
        if task[cmd]:
            return cmds_host[cmd](**task[cmd])
        else:
            return cmds_host[cmd]()
    else:
        if task[cmd]:
            return cmds_drone[cmd](group, **task[cmd])
        else:
            return cmds_drone[cmd](group)


def run_suite(host: DroneHost, path: str):
    """
    Run a suitea

    Args:
        path (str): Path to suite YAML file
    """
    results = []
    suite = load_suite(path)
    group = host.Group(suite["id"])
    group.assign(
        suite.get("drones_max", 1),
        suite.get("drones_min", 1),
        board=suite.get("board"),
    )

    loop_end = suite.get("repeat", 1) + 1
    for i in range(loop_end):
        logger.info(f"START {suite['id']} - {suite['name']} [{i}/{loop_end}]")
        for task in suite["tasks"]:
            results.append((task, run_task(group, task)))

    logger.info(f"Reset group {suite['id']}")
    group.reset()

    fail = 0
    if fail > 0:
        raise ExceptionClass(1000, f"{fail:d} iterations failed", "foo")

    return results


def validate_task(task, cmds_available):
    task = task.copy()
    for meta_cmd in meta_cmds:
        task.pop(meta_cmd, None)

    if len(task_data.keys()) > 1:
        raise ExceptionClass(1000, "More than one task identifier provided!", "foo")
    elif len(task.keys()) == 0:
        raise ExceptionClass(1000, "No task identifier provided!", "foo")

    if task.keys()[0] not in cmds_available:
        raise ExceptionClass(1000, "Unknown task identifier provided!", "foo")

    task_id = task_data.keys()[0]

    return task_id, task[task_id]


def run_task_drone(task):
    """
    Run a task remotely on udrone

    Args:
        task (dict): Task to run on drone
    """
    task_id, task_data = validate_task(task, cmds_drone)

    # TODO validate task args

    # per default we wait 10s for a reply
    timeout = 10
    # if a timeout value was passed, use it instead of the default
    if len(v) == 5:
        timeout = v[4]
    # check if the call has a payload
    if len(v) < 4:
        # no payload so do a flat call
        logger.debug('DRONE calling "' + v[2] + '"')
        return drone[v[1] - 1].call(v[2])
    else:
        # there is a payload, substitue global vars and iteration coutners
        payload = replace_tags(v[3], c)
        # issue the actual command
        logger.debug('DRONE calling "' + v[2] + '":' + json.dumps(payload))
        return drone[v[1] - 1].call(v[2], payload, task.get("timeout", 10))

    return cmd_drone


def load_suite(path: str) -> dict:
    suite_path = Path(path)
    assert suite_path.is_file(), "Config file not found"

    # do some validation

    return yaml.safe_load(suite_path.read_text())


def disband():
    host.disband()


#        logger.debug("ERROR no drones defined")
#
## iterate over the tests
# success = 0
# count = 0
# for t in test["test"]:
#    count = count + 1
#    try:
#        run_test(t)
#        logger.debug(f"PASS {count:d} " + test["id"])
#        success = success + 1
#        if t["sleep"]:
#            logger.debug(f"SLEEP {t['sleep']:d}")
#            time.sleep(t["sleep"])
#    except:
#        logger.debug(f"FAIL exception running {count:d} " + test["id"])
#        logger.debug(sys.exc_info())
#        time.sleep(5)
# d = 0
# while d < drone_count:
#    logger.debug(f"DRONE reset unit {d:d}")
#    cmd_drone(["DRONE", d, "!reset"], 1)
#    d = d + 1
#
# result = "FAIL"
# if success == len(test["test"]):
#    result = "PASS"
#
# logger.debug("RESULT " + result + f" {success:d}/{len(test['test']):d}")
