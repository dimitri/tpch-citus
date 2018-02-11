import time
import logging

from . import utils
from .task_pool import TaskPool

STREAM = "make -f Makefile.loader STREAM='%s' stream"


def stream(queries):
    output = utils.run_command(STREAM % (queries))
    return utils.parse_psql_timings(queries, output)


class StreamTaskPool(TaskPool):
    def report_progress(self):
        logging.info('%s: %d query streams executed in %gs',
                     self.name,
                     len(self.tasks_done),
                     time.monotonic() - self.start)


class Stream():
    def __init__(self, conf):
        self.conf = conf
        self.queries = self.conf.stream.queries
        self.duration = self.conf.stream.duration

        self.pool = StreamTaskPool(self.conf.scale.cpu, self.duration)

    def run(self, name):
        """Stream the given list of QUERIES on as many as CPU cores for given
        DURATION in minutes.

        """
        cpu = self.conf.scale.cpu

        logging.info("%s: Running TPCH with %d CPUs for %ds, stream %s",
                     name, cpu, self.duration, self.queries)

        qtimings, secs = self.pool.run(name, stream, self.queries)

        logging.info(
            "%s: executed %d streams of %d queries in %gs, using %d CPU",
            name, len(qtimings), len(qtimings[0]), secs, cpu)
        return
