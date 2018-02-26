import os
import os.path
import time
import logging
from datetime import datetime

from . import utils
from .task_pool import TaskPool
from .helpers import TpchComponent

MAKEFILE = os.path.join(os.path.dirname(__file__),
                        '..',
                        '..',
                        'Makefile.loader')

STREAM = "make -f %s DSN=%s STREAM='%s' stream"


def stream(dsn, queries, system):
    command = STREAM % (MAKEFILE, dsn, queries)
    out, err = utils.run_command(command)

    if err:
        logger = logging.getLogger('TPCH')
        logger.error(command)
        for line in err:
            logger.error('%s %s', system, line)

    return utils.parse_psql_timings(queries, out)


class StreamTaskPool(TaskPool):
    def report_progress(self):
        secs = time.monotonic() - self.start
        self.logger.info('%s: %d query streams executed in %gs, %gQPM',
                         self.system,
                         len(self.tasks_done),
                         secs,
                         len(self.tasks_done) / secs * 60.0)

    def handle_results(self, result):
        self.nbs += 1
        for name, duration in result.items():
            self.nbq += 1
            self.track.register_query_timings(self.stream_id, name, duration)


class Stream(TpchComponent):
    def __init__(self, conf, dsn, logger, track):
        super().__init__(conf, dsn, logger, track)
        # conf is expected to be a Stream namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.queries = self.conf.queries
        self.duration = self.conf.duration
        self.cpu = self.conf.cpu

        pause = 60
        if self.duration < 90:
            pause = 5

        self.pool = StreamTaskPool(self.cpu, self.duration, pause=pause)
        self.pool.track = self.track
        self.pool.logger = logger

    def run(self, system, phase):
        """Stream the given list of QUERIES on as many as CPU cores for given
        DURATION in minutes.

        """
        self.system = system
        self.log("Running TPCH with %d CPUs for %ds, stream %s",
                 self.cpu, self.duration, self.queries)

        start = datetime.now()

        self.pool.system = system
        self.pool.stream_id = self.track.register_job(phase, start)
        self.pool.nbs = 0       # nb stream
        self.pool.nbq = 0       # nb queries

        secs = self.pool.run(stream, self.dsn, self.queries, self.system)
        self.track.register_job_time(self.pool.stream_id, secs)

        self.log(
            "executed %d streams (%d queries) in %gs at %gQPM, using %d CPU",
            self.pool.nbs, self.pool.nbq,
            secs, self.pool.nbq / secs * 60.0, self.cpu)
        return
