import time
import logging

from . import utils
from .load import Load
from .stream import Stream
from .initdb import InitDB, run_schema_file
from .tracking import Tracking


class Schedule():
    def __init__(self, conf, system, kind='pgsql'):
        self.conf = conf
        self.system = system
        self.kind = kind

        self.track = None

    def run(self, name, schedule='schedule'):
        self.name = name

        # do we know how to do the job?
        if schedule not in self.conf.schedules:
            raise ValueError("%s not found in [run] section" % schedule)

        self.start = time.monotonic()
        self.schedule = self.conf.schedules[schedule]

        logging.info('%s: starting benchmark %s', self.system, self.name)

        self.track = Tracking(self.conf, self.system, self.name)
        self.track.register_benchmark(schedule)

        for phase in self.schedule:
            logging.info('%s: starting schedule %s', self.system, phase)

            # We have some hard-coded schedule phase names
            if phase == 'initdb':
                initdb = InitDB(self.conf, self.track, kind=self.kind)
                initdb.run(self.system)

            else:
                # And we have dynamic names, described in the config file
                job = self.conf.jobs[phase]

                if type(job).__name__ == 'Stream':
                    cmd = Stream(job, self.track)
                    cmd.run(self.system, phase)

                elif type(job).__name__ == 'Load':
                    cmd = Load(job, self.track)
                    cmd.run(self.system, phase)

                else:
                    raise ValueError(
                        "I don't know how to do %s, which is a %s" %
                        (job, type(job).__name__)
                    )

        self.end = time.monotonic()

        self.track.register_run_time(self.end - self.start)

        return
