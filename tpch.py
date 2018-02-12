#! /usr/bin/env python3

import os
import sys
import signal
import logging

from service import find_syslog, Service

from tpch import utils
from tpch import setup
from tpch.schedule import Schedule

import click
import os.path

CONF     = os.path.join(os.path.dirname(__file__), 'tpch.ini')
SCHEDULE = "full"
LOG_FILE = "/tmp/tpch.log"


class TpchService(Service):
    def __init__(self, name, pid_dir='/tmp'):
        super(TpchService, self).__init__(name, pid_dir=pid_dir)

    def run(self):
        self.bench.run(self.bname, self.schedule)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--ini", default=CONF, type=click.Path(exists=True))
@click.option("--log", default=LOG_FILE, type=click.Path())
@click.option("--debug", is_flag=True, default=False)
@click.option("--detach", is_flag=True, default=False)
@click.option("--kind", default='pgsql')
@click.option("--schedule", default=SCHEDULE)
@click.option("--name")
@click.option("--dsn", envvar='DSN')
@click.argument('system')
def benchmark(system, name, schedule, kind, dsn, ini, log, debug, detach):
    """Run a benchmark schedule/job on SYSTEM"""
    name = name or utils.compose_name()
    conf = setup.Setup(ini)

    logger = logging.getLogger('TPCH')
    llevel = logging.INFO
    lfmter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    if debug:
        llevel = logging.DEBUG

    logger.setLevel(llevel)

    fh = logging.FileHandler(log, 'w')
    fh.setLevel(llevel)
    fh.setFormatter(lfmter)
    logger.addHandler(fh)

    if detach:
        tpch = TpchService('TPCH', pid_dir='/tmp')
        tpch.bench = Schedule(conf, system, logger, dsn, kind=kind)
        tpch.bname = name
        tpch.schedule = schedule
        tpch.start()
    else:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(llevel)
        ch.setFormatter(lfmter)
        logger.addHandler(ch)

        bench = Schedule(conf, system, logger, dsn, kind=kind)
        bench.run(name, schedule)


@cli.command()
@click.option('--grammar', default='adverbs verbs')
def name(grammar):
    """Generate a name for a TPC-H benchmark run."""
    click.echo(utils.compose_name(grammar=grammar))


if __name__ == '__main__':
    cli()
