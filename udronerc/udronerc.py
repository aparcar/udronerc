import logging
import time
from pathlib import Path

import yaml
import json

from .dronegroup import DroneGroup
from .dronehost import DroneHost
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


def host_sleep(seconds: int = 5, comment: str = None):
    """
    Sleep for N seconds

    Args:
        group
        seconds: Seconds to sleep
    """
    msg = f"ok: [host]: sleep {seconds}s"
    if comment:
        msg += f' => "{comment}"'
    print(msg)
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


def uci_set(group: DroneGroup, data: dict, commit: bool = True):
    responses = group.call("uci_set", data)
    print(responses)

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
    responses = group.call(
        "ubus",
        {"path": "file", "method": "read", "param": {"path": path, "base64": base64},},
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


def print_results(results):
    for drone, result in results.items():
        msg = f"{result['status']}: [{drone}]"
        if result.get("data"):
            msg += " => "
            msg += json.dumps(result["data"], indent=4, sort_keys=True)
        print(msg)


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
    logger.info(f"TASK [{desc}]")

    if cmd.startswith("host"):
        if task[cmd]:
            cmds_host[cmd](**task[cmd])
        else:
            cmds_host[cmd]()
    else:
        if task[cmd]:
            results = cmds_drone[cmd](group, **task[cmd])
        else:
            results = cmds_drone[cmd](group)

        print_results(results)
        return results


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
        logger.info(f"PLAY {suite['id']} - {suite['name']} [{i}/{loop_end}]")
        for task in suite["tasks"]:
            results.append((task, run_task(group, task)))

    logger.info(f"Reset group {suite['id']}")
    group.reset()

    return results


def load_suite(path: str) -> dict:
    suite_path = Path(path)
    if not suite_path.is_file():
        logger.error(f"Config file {path} not found")
        quit(1)

    # TODO do some validation

    return yaml.safe_load(suite_path.read_text())


def disband():
    get_host().disband()


def whois(group, board):
    return get_host().whois(group, board=board)
