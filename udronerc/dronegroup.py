import logging
import threading
import time
from errno import ENOENT

from .constants import *
from .errors import *

# from .dronehost import DroneHost

logger = logging.getLogger(__name__)


class DroneGroup(object):
    """ The DroneGroup class stores active drones and run commands

    A drone group contains drones to run tests of a specific suite. It offers
    functions to assign new drones and run commands of all assigned drones.
    """

    def __init__(self, host, groupid: str):
        """
        Args:
            host (DroneHost): Initialized drone host
            groupid (str): Unique identifier for the group
        """
        self.host = host
        self.groupid = groupid
        self.idle_intval = UDRONE_IDLE_INTVAL
        self.timer = None
        self._timer_setup()
        self.seq = self.host.genseq()
        self.assigned_drones = set()
        logger.debug(f"Group {self.groupid} created.")

    def _timer_action(self):
        logger.debug("Group %s keep-alive timer triggered", self.groupid)
        if len(self.assigned_drones) > 0:
            self.host.whois(self.groupid, need=0, seq=0)
        self._timer_setup()

    def _timer_setup(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.idle_intval, self._timer_action)
        self.timer.setDaemon(True)
        self.timer.start()

    def _assign_drones(self, drones: list) -> list:
        """Send `!assign` command to list of drones

        Send the special `!assign` message to `drones` and checks their
        response. If they respond with with return code 0 the assignment was
        successfull.

        Args:
            drones (list): List of drone IDs to assign to the group

        Returns:
            set: Set of successfully assigned drones

        """
        logger.debug(f"Assign {drones} to {self.groupid}")
        responses = self.host.call_multi(
            drones, None, "!assign", {"group": self.groupid, "seq": self.seq}, "status"
        )
        assigned_drones = set()
        for drone_id, response in responses.items():
            if response["data"]["code"] == 0:
                assigned_drones.add(drone_id)
                self.assigned_drones.add(drone_id)

        return assigned_drones

    def assign(
        self, min_drones: int = 1, max_drones: int = None, board: str = "generic"
    ) -> list:
        """Assign new drones to a group

        Assigning works by sending a `!whois` broadcast message and wait for
        the responses of unassigned drones. A number of drones between
        `max_drones` and `min_drones` is then tried to assign, meaning the drones
        wont respond to other requests for that time.

        Args:
            max_drones (int): Maximal number of drones required
            min_drones (int): Mimimal number of drones required
            board (str): Limit assignment to specific board

        Returns:
            list: New member of group
        """
        logger.debug(
            f"Assign {min_drones}/{max_drones} {board} drones to {self.groupid}"
        )

        if not max_drones:
            max_drones = min_drones

        ingroup = self.host.whois(self.groupid, max_drones, board=board)

        if max_drones >= len(ingroup) >= min_drones:
            self.assigned_drones.update(list(ingroup.keys()))
            return list(ingroup.keys())

        available = list(
            self.host.whois(UDRONE_GROUP_DEFAULT, max_drones, board=board).keys()
        )[:max_drones]

        if len(available) < min_drones:
            logger.error("You must construct additional drones")
            quit(1)
        new_members = self._assign_drones(available)

        if len(new_members) < min_drones:
            max_drones -= len(new_members)
            available = list(self.host.whois(UDRONE_GROUP_DEFAULT, max_drones).keys())[
                :max_drones
            ]
            new_members += self._assign_drones(available)

        if len(new_members) < min_drones:
            if len(new_members) > 0:  # Rollback
                self.host.call_multi(new_members, None, "!reset", None, "status")
            raise DroneNotFoundError((ENOENT, "You must construct additional drones"))

        return new_members

    def reset(self, reset=None):

        if len(self.assigned_drones) < 1:
            return
        expect = self.assigned_drones.copy()
        self.host.reset(self.groupid, reset, expect)
        self.assigned_drones = expect
        if len(expect) > 0:
            raise DroneNotReachableError((ETIMEDOUT, "Request Timeout", expect))

    def request(self, msg_type, data=None, timeout=60):

        if len(self.assigned_drones) < 1:
            raise DroneNotFoundError((ENOENT, "Drone group is empty"))
        if msg_type[0] != "!":
            self.seq += 1
            seq = self.seq
        else:
            seq = self.host.genseq()

        pending = self.assigned_drones.copy()
        i = 0
        answers = {}
        start = time.time()
        now = start
        self._timer_setup()

        while len(pending) > 0 and (now - start) >= 0 and (now - start) < timeout:
            expect = pending.copy()
            i += 1
            if i % 2 == 1:
                answers.update(
                    self.host.call(self.groupid, seq, msg_type, data, expect=expect)
                )
            else:
                self.host.recv_until(
                    answers,
                    seq,
                    expect=expect,
                    timeout=min(10, timeout - (now - start)),
                )

            for drone in expect:  # Timed out
                answers[drone] = None
            for drone, ans in answers.items():
                if ans and ans["type"] == "accept":
                    answers[drone] = None  # In Progress
                elif drone in pending and ans is not None:
                    pending.remove(drone)
            now = time.time()
            self._timer_setup()
        return answers

    def call(self, msg_type, data=None, timeout=60, update=None):

        res = self.request(msg_type, data, timeout)
        if update:
            update.update(res)
        for drone, answer in res.items():
            if not answer:  # Some drone didn't answer
                raise DroneNotReachableError((ETIMEDOUT, "Request Timeout", [drone]))
            if drone not in self.assigned_drones:  # Some unknown drone answered
                raise DroneConflict([drone])
            if answer["type"] == "unsupported":
                raise DroneRuntimeError((EOPNOTSUPP, "Unknown Command", drone))
            try:
                if answer["type"] == "status" and answer["data"]["code"] > 0:
                    errstr = answer["data"].get("errstr")
                    errcode = answer["data"]["code"]
                    logger.error(f"drone {drone} responded with {errcode}: {errstr}")
                    quit(1)
            except Exception as e:
                if isinstance(e, DroneRuntimeError):
                    raise e
                else:
                    raise DroneRuntimeError((EPROTO, "Invalid Status Reply", drone))
        return update if update else res
