import time

from . import utils
from .load import Load
from .stream import Stream
from .initdb import InitDB
from .tracking import Tracking


class Schedule():
    def __init__(self, conf, system, logger, dsn, kind='pgsql'):
        self.dsn = dsn
        self.conf = conf
        self.system = system

        self.track = None
        self.logger = logger

        self.init_schema_files(kind)

    def init_schema_files(self, kind='pgsql'):
        if kind == 'pgsql':
            self.schema = self.conf.pgsql
        elif kind == 'citus':
            self.schema = self.conf.citus
        else:
            raise ValueError

    def run(self, name, schedule='schedule'):
        self.name = name

        # do we know how to do the job?
        if schedule not in self.conf.schedules:
            raise ValueError("%s not found in [run] section" % schedule)

        self.start = time.monotonic()
        self.schedule = self.conf.schedules[schedule]

        self.logger.info('%s: starting benchmark %s', self.system, self.name)

        self.track = Tracking(self.conf, self.system, self.name)
        self.track.register_benchmark(schedule)

        for phase in self.schedule:
            self.logger.info('%s: starting schedule %s', self.system, phase)

            # We have some hard-coded schedule phase names
            if phase == 'initdb':
                initdb = InitDB(self.dsn, self.conf, self.schema,
                                self.logger, self.track)
                initdb.run(self.system)

            else:
                # And we have dynamic names, described in the config file
                job = self.conf.jobs[phase]

                if type(job).__name__ == 'Stream':
                    cmd = Stream(job, self.dsn, self.logger, self.track)
                    cmd.run(self.system, phase)

                elif type(job).__name__ == 'Load':
                    cmd = Load(job,
                               self.dsn, self.schema, self.logger, self.track)
                    cmd.run(self.system, phase)

                else:
                    raise ValueError(
                        "I don't know how to do %s, which is a %s" %
                        (job, type(job).__name__)
                    )

        self.end = time.monotonic()

        self.track.register_run_time(self.end - self.start)

        return
