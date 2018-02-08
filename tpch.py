#! /usr/bin/env python3

# TPC-H driver
#
# Used in coordination the Makefile.loader in this directory to generate a
# TPC-H benchmark, from scratch, on an AWS infrastructure. The goal is to
# compare Core PostgreSQL, Citus Data Cloud, AWS RDS and AWS Aurora
# offerings when using a custom-made TPC-H work load.

import sys
import time

from tpch import commands, pooling, utils

def stream(name, queries, cpu, duration):
    """Stream the given list of QUERIES on as many as CPU cores for given
    DURATION in minutes.

    """
    print("Running TPCH on %s with %d CPUs for %ds, stream %s" %
          (name, cpu, duration, queries)
    )

    qtimings, secs = pooling.repeat_for_a_while_on_many_cores(
        name, cpu, duration, commands.stream, queries
    )

    print("%s: executed %d streams of %d queries in %gs, using %d CPU" %
          (name, len(qtimings), len(qtimings[0]), secs, cpu)
    )


def load(name, steps_range_as_string, cpu):
    "Load the next STEPs using as many as CPU cores."
    arglist = utils.expand_step_range(steps_range_as_string)

    res, secs = pooling.execute_on_one_core_per_arglist(
        name, cpu, commands.load, arglist
    )

    print("%s: loaded %d steps of data in %gs, using %d CPU" %
          (name, len(arglist), secs, cpu))


if __name__ == '__main__':
    command  = sys.argv[1]
    name     = sys.argv[2]
    args     = sys.argv[3]
    cpu      = int(sys.argv[4])

    if command == 'stream':
        duration = int(sys.argv[5])
        stream(name, args, cpu, duration)

    elif command == 'load':
        load(name, args, cpu)

    else:
        print("command '%s' is not supported" % (command))
