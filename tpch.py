#! /usr/bin/env python3

import os
import sys
import signal
import logging

from service import find_syslog, Service

from tpch.run import logs
from tpch.run import utils
from tpch.run import setup
from tpch.run.schedule import Schedule

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

    level = logging.INFO
    if debug:
        level = logging.DEBUG

    logger = logs.logger(level)
    logs.setup_file_logger(logger, log, level)

    if detach:
        tpch = TpchService('TPCH', pid_dir='/tmp')
        tpch.bench = Schedule(conf, system, logger, dsn, kind=kind)
        tpch.bname = name
        tpch.schedule = schedule
        tpch.start()
    else:
        logs.setup_stdout_logger(logger, level)
        bench = Schedule(conf, system, logger, dsn, kind=kind)
        bench.run(name, schedule)


@cli.command()
@click.option('--grammar', default='adverbs verbs')
def name(grammar):
    """Generate a name for a TPC-H benchmark run."""
    click.echo(utils.compose_name(grammar=grammar))


if __name__ == '__main__':
    cli()
