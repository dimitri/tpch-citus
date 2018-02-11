import time
import logging

from . import utils
from .load import Load
from .stream import Stream
from .initdb import InitDB, run_schema_file
from .results import Results


class Schedule():
    def __init__(self, conf, system, kind='pgsql'):
        self.conf = conf
        self.system = system
        self.kind = kind

        self.results = None

    def run(self, name, schedule='schedule'):
        self.name = name

        # do we know how to do the job?
        if schedule not in self.conf.schedules:
            raise ValueError("%s not found in [run] section" % schedule)

        self.schedule = self.conf.schedules[schedule]

        logging.info('%s: starting benchmark %s', self.system, self.name)

        self.results = Results(self.conf, self.system, self.name)
        self.results.register_benchmark()

        for phase in self.schedule:
            logging.info('%s: starting schedule %s', self.system, phase)

            # We have some hard-coded schedule phase names
            if phase == 'initdb':
                initdb = InitDB(self.conf, self.results, kind=self.kind)
                initdb.run(self.system)

            else:
                # And we have dynamic names, described in the config file
                job = self.conf.jobs[phase]

                if type(job).__name__ == 'Stream':
                    cmd = Stream(job, self.results)
                    cmd.run(self.system, phase)

                elif type(job).__name__ == 'Load':
                    cmd = Load(job, self.results)
                    cmd.run(self.system, phase)

                else:
                    raise ValueError(
                        "I don't know how to do %s, which is a %s" %
                        (job, type(job).__name__)
                    )

        return
