import time
import logging
from datetime import datetime

from . import utils
from .task_pool import TaskPool

STREAM = "make -f Makefile.loader STREAM='%s' stream"


def stream(queries):
    output = utils.run_command(STREAM % (queries))
    return utils.parse_psql_timings(queries, output)


class StreamTaskPool(TaskPool):
    def report_progress(self):
        logging.info('%s: %d query streams executed in %gs',
                     self.system,
                     len(self.tasks_done),
                     time.monotonic() - self.start)

    def handle_results(self, result):
        self.nbs += 1
        for name, duration in result.items():
            self.nbq += 1
            self.track.register_query_timings(self.stream_id, name, duration)

class Stream():
    def __init__(self, conf, track):
        # conf is expected to be a Stream namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.conf = conf
        self.queries = self.conf.queries
        self.duration = self.conf.duration
        self.cpu = self.conf.cpu

        self.track = track

        self.pool = StreamTaskPool(self.cpu, self.duration)
        self.pool.track = self.track

    def run(self, system, phase):
        """Stream the given list of QUERIES on as many as CPU cores for given
        DURATION in minutes.

        """
        logging.info("%s: Running TPCH with %d CPUs for %ds, stream %s",
                     system, self.cpu, self.duration, self.queries)

        start = datetime.now()

        self.pool.system = system
        self.pool.stream_id = self.track.register_job(phase, start)
        self.pool.nbs = 0       # nb stream
        self.pool.nbq = 0       # nb queries

        secs = self.pool.run(stream, self.queries)

        self.track.register_job_time(self.pool.stream_id, secs)

        logging.info(
            "%s: executed %d streams (%d queries) in %gs, using %d CPU",
            system, self.pool.nbs, self.pool.nbq, secs, self.cpu)
        return
