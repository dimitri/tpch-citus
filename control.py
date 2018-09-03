#! /usr/bin/env python3

import os
import sys
import click
import shutil
import os.path
import logging
import zipfile

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
@click.option('--infra', type=click.Path(exists=True), required=True)
@click.option('--sched', type=click.Path(exists=True), required=True)
def setup(infra, sched, name):
    """Set-up a TPC-H benchmark: infra.ini, schedule.ini"""
    if not name:
        name = tpch.run.utils.compose_name()

    tpch.control.utils.setup_out_dir(name, infra, sched)
    click.echo(name)


@cli.command()
@click.argument('name')
@click.argument('schedule')
@click.argument('system', nargs=-1)
def register(name, schedule, system):
    """Register a schedule and the target systems."""
    r = bench.Run(name)
    r.register(schedule, system)
    click.echo('%s: registered schedule %s for systems %s'
               % (name, schedule, ", ".join(r.sysnames)))


@cli.command()
@click.option('--system')
@click.argument('name')
def prepare(name, system):
    """Run the benchmarks"""
    r = bench.Run(name, system)
    r.prepare()
    return


@cli.command()
@click.option('--schedule')
@click.option('--system')
@click.argument('name')
def benchmark(name, schedule, system):
    """Run the benchmarks"""
    r = bench.Run(name, system)
    r.prepare()
    r.start(schedule)
    return


@cli.command()
@click.option('--name')
@click.option('--running', is_flag=True, default=False)
@click.option('--db', default=RES_DB_CONNSTR)
def status(name, running, db):
    """Display infra status and becnhmark logs"""
    if name:
        r = bench.Run(name, resdb=db)
        r.status(with_results=False)

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)
            if running:
                if run.is_ready():
                    run.status(with_results=False)
            else:
                run.status(with_results=False)
    return


@cli.command()
@click.option('--name')
@click.option('--orphans', is_flag=True, default=False)
@click.option('--dsn', is_flag=True, default=False)
def infra(name, orphans, dsn):
    """Display infra in use by benchmarks"""
    if name:
        run = bench.Run(name)
        run.list()
        run.list_infra(dsn)

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name)

            if orphans:
                # only list infra running for no reasons
                if run.has_infra() and not run.tpch_is_running():
                    run.list()
                    run.list_infra(dsn)

            else:
                # here we list everything we know
                run.list_infra(dsn)
    return


@cli.command()
@click.option('--name')
@click.option('--running', is_flag=True, default=False)
@click.option('--db', default=RES_DB_CONNSTR)
def list(db, name, running):
    """List currently known benchmarks."""
    if name:
        run = bench.Run(name, resdb=db)
        run.list()
        print()

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)
            if running:
                if run.is_ready():
                    run.list()
            else:
                run.list()
            print()


@cli.command()
@click.option('--name', required=True)
@click.option('--system')
@click.option('-f', is_flag=True, default=False)
@click.option('-n', default=10)
def tail(name, system, n, f):
    """Connects to the loaders and tail -f tpch.log"""
    r = bench.Run(name, system)
    r.tail(follow=f, n=n)
    return


@cli.command()
@click.option('--name')
@click.option('--system')
@click.option('--running', is_flag=True, default=True)
@click.option('--db', default=RES_DB_CONNSTR)
def update(name, system, running, db):
    """Fetch logs and intermediate results from loaders"""
    try:
        tpch.control.utils.maybe_install_resdb(db)
    except Exception as err:
        print("Can't connect to %s: %s" % (db, err))
        return

    if name:
        r = bench.Run(name, system, resdb=db)
        r.update()

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, system, resdb=db)
            run.update(tail=False, results=False)

        # rather than printing a large progress report for each running
        # benchmark we just updated, show the shorter list information
        # screen at the end.
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)
            if run.is_ready():
                print()
                run.status()

    print()


@cli.command()
@click.option('--name')
@click.option('--db', default=RES_DB_CONNSTR)
@click.option('--running', is_flag=True, default=False)
def results(name, db, running):
    """Show local benchmark results"""
    if name:
        run = bench.Run(name, resdb=db)
        run.results(verbose=True)
        print()

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)

            if running:
                if run.is_ready():
                    run.results(verbose=True)
                    print()
            else:
                run.results(verbose=True)
                print()
    return


@cli.command()
@click.option('--name')
@click.option('--db', default=RES_DB_CONNSTR)
def merge_results(name, db):
    """Merge local results from loaders"""
    try:
        tpch.control.utils.maybe_install_resdb(db)
    except Exception as err:
        print("Can't connect to %s: %s" % (db, err))
        return

    if name:
        run = bench.Run(name, resdb=db)
        run.merge_results()
        print()
        run.list()
        print()

    else:
        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)
            run.merge_results()
        print()

        for name in tpch.control.utils.list_runs():
            run = bench.Run(name, resdb=db)
            run.list()
            print()


@cli.command()
@click.argument('name')
@click.option('--system')
def cancel(name, system):
    """Terminate loaders, cancel currently running benchmark"""
    r = bench.Run(name, system)
    r.cancel()


@cli.command()
@click.option('--name')
@click.option('--system')
@click.option('--orphans', is_flag=True, default=False)
def terminate(name, system, orphans):
    """Terminate loaders, delete database instances"""
    if orphans:
        for name in tpch.control.utils.list_runs():
            r = bench.Run(name, system)

            if r.has_infra() and not r.tpch_is_running():
                r.terminate()
    else:
        r = bench.Run(name, system)
        r.terminate()

@cli.command()
@click.argument('archive', type=click.Path())
@click.argument('name', nargs=-1)
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
def export(archive, name, verbose, force):
    "Export bench results into an archive file."
    if force and os.path.exists(archive):
        os.remove(archive)

    try:
        with zipfile.ZipFile(archive, mode='x') as zip:
            if name:
                # the --name argument can be used several times
                # so that we get a list of names here
                namelist = name

                for name in namelist:
                    run = bench.Run(name)
                    print("Archiving results for %s" % run.name)
                    for fn in run.list_result_files():
                        if verbose:
                            print("  %s" % fn)
                        zip.write(fn)
            else:
                for name in tpch.control.utils.list_runs():
                    run = bench.Run(name)
                    print("Archiving results for %s" % run.name)
                    for fn in run.list_result_files():
                        if verbose:
                            print("  %s" % fn)
                        zip.write(fn)

    except FileExistsError as err:
        print("Creation of %s failed: %s" % (archive, err))


@cli.command(name='import')
@click.argument('archive', type=click.Path(exists=True))
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@click.option('--db', default=RES_DB_CONNSTR)
def import_(archive, force, verbose, db):
    "Import an archive of results"
    log = logging.getLogger('TPCH')
    log.info("Extracting TPCH results from archive %s", archive)

    try:
        tpch.control.utils.maybe_install_resdb(db)
    except Exception as err:
        print("Can't connect to %s: %s" % (db, err))
        return

    runs = []
    skipped = []
    with zipfile.ZipFile(archive, mode='r') as zip:
        current_run = None
        for fn in zip.namelist():
            if fn[0:8] != 'aws.out/':
                print("ignoring file %s" % fn)
            relpath = fn[8:]

            run = relpath.split('/')[0]

            if run != current_run:
                current_run = run
                runs.append(current_run)
                if verbose:
                    print("Importing results for run '%s'" % current_run)

            if os.path.exists(fn) and not force:
                if verbose:
                    print("  skipping %s" % fn)
                if current_run not in skipped:
                    skipped.append(current_run)
                continue

            if verbose:
                print("  %s" % fn)

            zip.extract(fn)

    for run in runs:
        if run not in skipped:
            b = bench.Run(run)
            b.merge_results()

        else:
            if verbose:
                print("Skipped files in run '%s', use --force to override"
                      % run)

    print()
    for run in runs:
        if run not in skipped:
            b = bench.Run(run)
            b.list()
            print()
            b.results(verbose=True)
            print()

    return


if __name__ == '__main__':
    logger = logging.getLogger('TPCH')

    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(ch)

    cli()
