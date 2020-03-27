from ..dronegroup import DroneGroup
import logging

logger = logging.getLogger(__name__)


def checkip(
    group: DroneGroup,
    interface="lan",
    check_ipv4: bool = True,
    check_ipv6: bool = False,
    specific_ipv4: str = None,
    specific_ipv6: str = None,
):
    """Check drone IP state on specified interface

    Args:
        group (DroneGroup): Group with drones to check
        interface (str): Interface name to check for IP
        check_ipv4 (bool): Check if interface has IPv4 address
        check_ipv6 (bool): Check if interface has iPv6 address
        specific_ipv4 (str): IPv4 that specific be assigned to interface
        specific_ipv6 (str): IPv6 that specific be assigned to interface

    """
    logger.debug(
        f"{interface=} {check_ipv4=} {check_ipv6=} {specific_ipv4=} {specific_ipv6=}"
    )
    success = {}
    responses = group.call(
        "ubus", {"path": f"network.interface.{interface}", "method": "dump"}
    )
    for response in responses:
        success[response["from"]] = True
        if check_ipv4:
            ipv4_addresses = response["data"].get("ipv4-address", [])
            if not specific_ipv4:
                if len(ipv4_addresses) > 0:
                    success[response["from"]] = False
            else:
                found = False
                for ip in ipv4_addresses:
                    if ip["address"] == specific_ipv4:
                        found = True
                if not found:
                    success[response["from"]] = False

        if check_ipv6:
            ipv6_addresses = response["data"].get("ipv6-address", [])
            if not specific_ipv6:
                if len(ipv6_addresses) > 0:
                    success[response["from"]] = False
            else:
                found = False
                for ip in ipv6_addresses:
                    if ip["address"] == specific_ipv6:
                        found = True
                if not found:
                    success[response["from"]] = False

    return success
