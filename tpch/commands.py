import os
import sys
import shlex
import subprocess

LOAD   = 'make -f Makefile.loader S=%s load'
STREAM = "make -f Makefile.loader STREAM='%s' stream"

def run_command(command, verbose=True):
    "Run a command in a subprocess"
    cmd = shlex.split(command)

    with subprocess.Popen (cmd, stdout=subprocess.PIPE) as p:
        return p.stdout.readlines()


def load(step):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    run_command(LOAD % (step))
    return


def stream(queries):
    output = run_command(STREAM % (queries))

    # parse the output of the command, which should contain a Time:
    # entry for each query in the stream
    timings = {}
    qstream = queries.split(" ")
    i = 0
    for line in output:
        if line and line.startswith(b'Time: '):
            timing = line[len(b'Time: '):-1]
            timings[qstream[i]] = timing
            i = i+1

    return timings
