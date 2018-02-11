#! /usr/bin/env python3

import sys
import logging
import pprint

from tpch import utils
from tpch import setup
from tpch.schedule import Schedule

import click

CONF = "tpch.ini"
SCHEDULE = "full"


@click.group()
def cli():
    pass


@cli.command()
@click.option("--ini", default=CONF, type=click.Path(exists=True))
@click.option("--debug", is_flag=True, default=False)
@click.option("--kind", default='pgsql')
@click.option("--schedule", default=SCHEDULE)
@click.option("--name")
@click.argument('system')
def benchmark(system, name, schedule, kind, ini, debug):
    """Run a benchmark schedule/job on SYSTEM"""
    name = name or utils.compose_name()
    conf = setup.Setup(ini)
    utils.setup_logging(debug)

    bench = Schedule(conf, system, kind=kind)
    bench.run(name, schedule)


@cli.command()
@click.option('--grammar', default='adverbs verbs')
def name(grammar):
    """Generate a name for a TPC-H benchmark run."""
    click.echo(utils.compose_name(grammar=grammar))


if __name__ == '__main__':
    cli()
