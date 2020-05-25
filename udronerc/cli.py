import json
import logging
from pathlib import Path

import click
import yaml

import udronerc.udronerc

with open("config.yml") as c:
    conf = yaml.safe_load(c.read())

logging.basicConfig(level=conf["log_level"])
logger = logging.getLogger(__name__)


@click.group()
def cli():
    logger.info("Starting CLI")


@cli.command()
def disband():
    udronerc.udronerc.disband()


@cli.group()
def suite():
    """suite related commands"""
    pass


@suite.command()
@click.argument("path")
def run(path):
    """Run suite at given path"""
    host = udronerc.udronerc.get_host()
    results_suite = udronerc.udronerc.run_suite(host, path)
    Path("results.json").write_text(json.dumps(results_suite, indent="  "))
    logger.info(f"Stored suite results to results.json")


if __name__ == "__main__":
    cli()
