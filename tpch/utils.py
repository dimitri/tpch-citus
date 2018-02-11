import shlex
import subprocess
import logging
import os.path
import random

LOG_LEVEL  = logging.INFO
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'

def setup_logging(debug=False):
    level = LOG_LEVEL
    if debug:
        level = logging.DEBUG

    logging.basicConfig(format=LOG_FORMAT, level=level)


def run_command(command, verbose=False):
    "Run a command in a subprocess"
    cmd = shlex.split(command)

    if verbose:
        print(cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as p:
        b = p.stdout.read()
        s = b.decode('utf-8')
        return s.splitlines()


def parse_psql_timings(queries, output):
    "Parse psql Time: output when \timing is used."
    timings = {}
    qstream = queries.split(" ")
    i = 0
    for line in output:
        if line and line.startswith(u'Time: '):
            ms_pos = line.find('ms') + len('ms')
            timing = line[len(u'Time: '):ms_pos]
            timings[qstream[i]] = timing
            i = i + 1

    return timings


def expand_step_range(steps):
    """Explode the notation 2..10 into the Python list

    [2, 3, 4, 5, 6, 7, 8, 9, 10]
    """
    try:
        step_range = steps.split('..')

        if len(step_range) == 1:
            return [int(step_range[0])]

        elif len(step_range) == 2:
            start, end = int(step_range[0]), int(step_range[1])

            return [start + x for x in range(end - start + 1)]

        else:
            return []
    except Exception:
        return []


def compose_name(grammar='verbs adverbs', tokens='tpch-pg/src/dists.dss'):
    distfile = os.path.join(os.path.dirname(__file__), '..', tokens)

    dists = {}
    for d in grammar.split():
        dists[d] = []

    n = 0
    current_dist = None

    with open(distfile, 'r') as df:
        for line in df:
            n += 1
            line = line[:-1]

            if current_dist:
                if line.lower() == 'end %s' % current_dist:
                    current_dist = None

                else:
                    token = line.split('|')[0]
                    if token != 'COUNT':
                        dists[current_dist].append(token)

            else:
                for d in dists.keys():
                    if line.lower() == 'begin %s' % d:
                        current_dist = d

    name = []
    for d in grammar.split():
        n = random.randrange(len(dists[d]))
        name.append(dists[d][n])

    return '_'.join(name)
