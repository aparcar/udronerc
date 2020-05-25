import json
import logging
from pathlib import Path

import click
import yaml

import udronerc.udronerc

from udronerc.constants import UDRONE_GROUP_DEFAULT

with open("config.yml") as c:
    conf = yaml.safe_load(c.read())

logging.basicConfig(level=conf["log_level"])
logger = logging.getLogger(__name__)


@click.group()
def cli():
    logger.info("Starting CLI")


@cli.command()
@click.option("--board", default="generic", help="Limit to specific board type")
def whois(board):
    """Return number and names of all active drones"""
    whois = list(udronerc.udronerc.whois(UDRONE_GROUP_DEFAULT, board).keys())
    logger.info(f"Active drones ({len(whois)}): {whois}")


@cli.command()
def disband():
    udronerc.udronerc.disband()


@cli.group()
def suite():
    """Suite related commands"""
    pass


@suite.command()
@click.argument("path")
def run(path):
    """Run test suite at given path"""
    host = udronerc.udronerc.get_host()
    results_suite = udronerc.udronerc.run_suite(host, path)
    Path("results.json").write_text(json.dumps(results_suite, indent="  "))
    logger.info("Stored suite results to results.json")


if __name__ == "__main__":
    cli()
