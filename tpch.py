#! /usr/bin/env python3

# TPC-H driver
#
# Used in coordination with Makefile, Makefile.loader and the ec2driver.py
# in this directory to generate a TPC-H benchmark, from scratch, on an AWS
# infrastructure. The goal is to compare Core PostgreSQL, Citus Data Cloud,
# AWS RDS and AWS Aurora offerings when using a custom-made TPC-H work load.

import os, sys, shlex, subprocess

STREAM_COMMAND = 'make -f Makefile.loader stream'

def stream(dsn, queries):
    "Run a stream of QUERIES and get the timing result."
    os.putenv("DSN", dsn)
    os.putenv("STREAM", queries)

    command = shlex.split(STREAM_COMMAND)
    print(command)

    with subprocess.Popen (command, stdout=subprocess.PIPE) as p:
        for line in p.stdout.readlines():
            # parse the output of the command, which should contain a Time:
            # entry for each query in the stream
            qstream = queries.split(" ")
            i = 0
            if line and line.startswith(b'Time: '):
                timing = line[len(b'Time: '):-1]
                print("Q%s: %s" % (qstream[i], timing))
                i = i+1


def refresh(dsn):
    "Refresh the database with new data"
    pass



if __name__ == '__main__':
    stream(sys.argv[1], sys.argv[2])

