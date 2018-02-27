#! /usr/bin/env python3

import os
import sys
import click
import shutil
import os.path
import logging

from pathlib import Path

from tpch import bench
from tpch import system

import tpch.run.utils
import tpch.run.setup
import tpch.infra.setup
import tpch.control.utils
import tpch.control.setup


RES_DB_CONNSTR = 'postgresql://localhost/tpch-results'


@click.group()
def cli():
    """TPC-H driver to control running tests.

A TPC-H setup consists of an infrastructure to run the tests (infra.ini) and
a test schedule definition (tpch.ini). First edit setup, and then register
it with the schedule and systems you want to use for your next run.

One you have that, you can start benchmarking. The real work happens on an
AWS instance, the loader. There's one loader per system being tested. The
control scripts uses rsync and ssh to control the loader instances.

 1. ./control.py setup       ; note the name returned

 2. ./control.py register  <schedule> <system> [ <system> ... ]

 3. ./control.py benchmark <name>  ; with name from step 1

 4. ./control.py update <name>     ; and see what's happening

 5. ./control.py tail <name>     ; and see what's happening

    """
    pass


@cli.command()
@click.option("--name")
@click.argument('infra', type=click.Path(exists=True))
@click.argument('config', type=click.Path(exists=True))
def setup(infra, config, name):
    """Set-up a TPC-H benchmark: infra.ini, tpch.ini"""
    if not name:
        name = tpch.run.utils.compose_name()

    tpch.control.utils.setup_out_dir(name, infra, config)
    click.echo(name)


@cli.command()
@click.argument('name')
@click.argument('schedule')
@click.argument('system', nargs=-1)
def register(name, schedule, system):
    """Register a schedule and the target systems."""
    r = bench.Run(name)
    r.register(system, schedule)
    click.echo('%s: registered schedule %s for systems %s'
               % (name, schedule, ", ".join(system)))


@cli.command()
@click.option('--schedule')
@click.option('--system')
@click.argument('name')
def benchmark(name, schedule, system):
    """Run the benchmarks"""
    # prepare the infra
    r = bench.Run(name, system)
    r.prepare(schedule)
    r.start(schedule)
    return


@cli.command()
@click.argument('name')
def status(name):
    """Display infra status and becnhmark logs"""
    r = bench.Run(name)
    r.status()
    return


@cli.command()
def list():
    """List currently known benchmarks."""
    p = Path('./aws.out/')
    for f in p.iterdir():
        if f.is_dir() and os.path.exists(os.path.join(f, 'run.ini')):
            r = bench.Run(f.name)
            r.list()
            print()

@cli.command()
@click.argument('name')
@click.option('--system')
@click.option('-f', is_flag=True, default=False)
def tail(name, system, f):
    """Connects to the loaders and tail -f tpch.log"""
    r = bench.Run(name, system)
    r.tail(f)
    return


@cli.command()
@click.argument('name')
@click.option('--system')
def update(name, system):
    """Fetch logs and intermediate results from loaders"""
    r = bench.Run(name, system)
    r.update()


@cli.command()
@click.argument('name')
@click.option('--system')
def cancel(name, system):
    """Terminate loaders, cancel currently running benchmark"""
    r = bench.Run(name, system)
    r.cancel()


@cli.command()
@click.argument('name')
def terminate(name):
    """Terminate loaders, delete database instances"""
    r = bench.Run(name)
    r.terminate()


if __name__ == '__main__':
    logger = logging.getLogger('TPCH')

    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(ch)

    cli()
