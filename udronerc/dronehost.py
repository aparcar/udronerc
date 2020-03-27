from errno import EWOULDBLOCK
import binascii
import json
import logging
import os
import select
import socket
import struct
import time
import fcntl

from .constants import *
from .errors import *
from .dronegroup import DroneGroup

logger = logging.getLogger(__name__)


class DroneHost(object):
    def __init__(self, local_ip=None, hostid=None):
        if not hostid:
            self.hostid = f"udronerc_{binascii.hexlify(os.urandom(3)).decode()}"
        else:
            self.hostid = hostid

        logger.info(f"Initializing host on {local_ip} with ID {self.hostid}")
        self.addr = UDRONE_ADDR
        self.resent_strategy = UDRONE_RESENT_STRATEGY
        self.maxsize = UDRONE_MAX_DGRAM

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", 0))

        self.socket.setsockopt(
            socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip)
        )

        self.socket.setblocking(0)

        self.poll = select.poll()
        self.poll.register(self.socket, select.POLLIN)

        self.groups = []

    def get_ip_address(self, interface: str) -> str:
        """
        Get IP of a local interface

        Args:
            interface (str): name of local interface

        Returns:
            str: IP address of interface
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(),
                0x8915,
                struct.pack("256s", interface[:15].encode("utf-8")),  # SIOCGIFADDR
            )[20:24]
        )

    def genseq(self) -> int:
        """
        Generate random sequence number

        Returns:
            int: generated sequence
        """
        return struct.unpack("=I", os.urandom(4))[0] % 2000000000

    def send(self, to: str, seq: int, msg_type: str, data: dict = {}):
        """
        Send message to drone

        Args:
            to (str): receiving group
            seq (int): sequence number
            msg_type (str): type of message to receive
            data (dict): data to send to node
        """
        msg = {
            "from": self.hostid,
            "to": to,
            "type": msg_type,
            "seq": seq,
            "data": data,
        }
        packet = json.dumps(msg, separators=(",", ":"))
        logger.debug(f"Sending: {packet}")
        self.socket.sendto(packet.encode("utf-8"), self.addr)

    def recv(self, seq: int, msg_type: str = None) -> dict:
        """
        Recevie messages from drones

        Args:
            seq (int): sequence number
            msg_type (str): type of message to receive

        Returns:
            dict: received message from drone
        """
        while True:
            try:
                msg = json.loads(self.socket.recv(self.maxsize))
                if (
                    msg["from"]
                    and msg["type"]
                    and msg["to"] == self.hostid
                    and (not msg_type or msg["type"] == msg_type)
                    and (not seq or msg["seq"] == seq)
                ):
                    logger.debug(f"Received: {msg}")
                    return msg
            except Exception as e:
                if isinstance(e, socket.error) and e.errno == EWOULDBLOCK:
                    return None

    def recv_until(
        self,
        answers: dict,
        seq: int,
        msg_type: str = None,
        timeout: int = 1,
        expect: list = None,
    ):
        """
        Recevie messages from drones until requirement is fulfilled

        Args:
            answers (dict): Empty dict to be filled with received answers
            seq (int): sequence number
            msg_type (str): type of message to receive
            timeout (int): number of seconds before receiving timeouts
            expect (list): list of drones expected to anser
        """

        logger.debug(
            "Receiving replies for seq %i for %.1f secs expecting %s",
            seq,
            timeout,
            expect,
        )
        start = time.time()
        now = start
        while (
            (now - start) >= 0
            and (now - start) < timeout
            and (expect is None or len(expect) > 0)
        ):
            self.poll.poll((timeout - (now - start)) * 1000)
            while True:
                msg = self.recv(seq, msg_type)
                if msg:
                    answers[msg["from"]] = msg
                    if expect is not None and msg["from"] in expect:
                        expect.remove(msg["from"])
                elif not msg:
                    break
            now = time.time()

    def call(
        self,
        to: str,
        seq: int,
        msg_type: str,
        data: dict = None,
        resp_type: str = None,
        expect: list = None,
    ) -> dict:
        """
        Send data to drone and receive response

        Args:
            to (str): selected group
            seq (int): sequence number
            msg_type (str): send message of type
            data (dict): data to send to group
            resp_type (str): receive message of type
            expect (list): list of drones expected to anser

        Returns:
            dict: received message from drones
        """

        if not seq:
            seq = self.genseq()

        answers = {}

        for timeout in self.resent_strategy:
            self.send(to, seq, msg_type, data)
            self.recv_until(answers, seq, resp_type, timeout, expect)
            if expect is not None and len(expect) == 0:
                break
        return answers

    def call_multi(
        self,
        nodes: list,
        seq: int,
        msg_type: str,
        data: dict = None,
        resp_type: str = None,
    ) -> dict:
        """
        Send data to multiple drones and receive responses

        Args:
            nodes (list): selected drones
            seq (int): sequence number
            msg_type (str): send message of type
            data (dict): data to send to group
            resp_type (str): receive message of type

        Returns:
            dict: received message from drones
        """

        if not seq:
            seq = self.genseq()

        answers = {}

        for timeout in self.resent_strategy:
            for node in nodes:
                self.send(node, seq, msg_type, data)
            self.recv_until(answers, seq, resp_type, timeout, nodes)
            if len(nodes) == 0:
                break
        return answers

    def whois(
        self, group: str, need: int = 1, seq: int = None, board: str = None
    ) -> dict:
        """
        Return online drones

        Args:
            group (str): limit request to specific group
            need (int): minimum number of ansers
            seq (int): sequence number
            board (str): limit request to specific board

        Returns:
            dict: received answers of boards
        """
        logger.debug(f"Group {group} needs {need} {board} drones")
        answers = {}
        if seq is None:
            seq = self.genseq()
        for timeout in self.resent_strategy:
            data = {}
            if board:
                data["board"] = board

            self.send(group, seq, "!whois", data)
            if need == 0:
                break
            self.recv_until(answers, seq, "status", timeout)
            if need and len(answers) >= need:
                break

        return answers

    def reset(self, whom, how=None, expect=None):
        data = {"how": how} if how else None
        return self.call(whom, None, "!reset", data, "status", expect)

    def Group(self, groupid: str, absolute: bool = False):
        """Create new group

        Args:
            groupid (str): Name of the new group
            absolute (bool): Prefix group name with hostid

        Returns:
            Group: Newly created group
        """
        if not absolute:
            groupid = f"{self.hostid}_{groupid}"

        group = DroneGroup(self, groupid)
        self.groups.append(group)
        return group

    def disband(self, reset=None):
        for group in self.groups:
            group.reset(reset)
        self.groups = []
