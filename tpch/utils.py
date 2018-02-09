import shlex
import subprocess


def run_command(command, verbose=False):
    "Run a command in a subprocess"
    cmd = shlex.split(command)

    if verbose:
        print(cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as p:
        return p.stdout.readlines()


def parse_psql_timings(queries, output):
    "Parse psql Time: output when \timing is used."
    timings = {}
    qstream = queries.split(" ")
    i = 0
    for line in output:
        if line and line.startswith(b'Time: '):
            timing = line[len(b'Time: '):-1]
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
