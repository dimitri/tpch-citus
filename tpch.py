#! /usr/bin/env python3

import os
import sys
import signal
import logging

from tpch import utils
from tpch import setup
from tpch.schedule import Schedule

import click
import cotyledon

CONF = "tpch.ini"
SCHEDULE = "full"


class TpchService(cotyledon.Service):
    def __init__(self, worker_id, system, name, conf, kind, schedule):
        super(TpchService, self).__init__(worker_id)
        self.system = system
        self.name = name
        self.conf = conf
        self.kind = kind
        self.schedule = schedule

    def run(self):
        self.bench = Schedule(self.conf, self.system, kind=self.kind)
        self.bench.run(self.name, self.schedule)

        # we're done, signal the Service Manager that we can quit now
        os.kill(os.getppid(), signal.SIGINT)


class TpchManager(cotyledon.ServiceManager):
    def __init__(self, system, name, conf, kind, schedule):
        super(TpchManager, self).__init__()

        self.service_id = self.add(TpchService, 1,
                                   (system, name, conf, kind, schedule))


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

    # Run as a managed service so that we continue with our benchmark in the
    # background even when we lose e.g. the ssh connection to the shell
    TpchManager(system, name, conf, kind, schedule).run()

@cli.command()
@click.option('--grammar', default='adverbs verbs')
def name(grammar):
    """Generate a name for a TPC-H benchmark run."""
    click.echo(utils.compose_name(grammar=grammar))


if __name__ == '__main__':
    cli()
