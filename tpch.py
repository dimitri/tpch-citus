#! /usr/bin/env python3

import sys
import logging
from tpch import setup
from tpch.load import Load
from tpch.stream import Stream
from tpch.initdb import InitDB

import click

CONF = "tpch.ini"
LOG_LEVEL = logging.INFO


@click.group()
def cli():
    pass


@cli.command()
@click.option("--ini", default=CONF, type=click.Path(exists=True))
@click.option("--kind", default='pgsql')
@click.argument('name')
@click.argument('phase')
def load(name, phase, ini, kind, debug):
    conf = setup.Setup(ini)

    if phase == 'initdb':
        cmd = InitDB(conf, kind=kind, phase=phase)
    else:
        cmd = Load(conf, phase)

    cmd.run(name)


@cli.command()
@click.option("--ini", default=CONF, type=click.Path(exists=True))
@click.argument('name')
def stream(name, ini):
    conf = setup.Setup(ini)
    cmd = Stream(conf)
    cmd.run(name)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        level=LOG_LEVEL)
    logging.info('Hello there')
    cli()
