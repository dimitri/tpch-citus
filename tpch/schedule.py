import os
import time
from multiprocessing import Process

from . import utils, logs
from .load import Load
from .stream import Stream
from .initdb import InitDB
from .tracking import Tracking
from .helpers import TpchComponent


class Schedule(TpchComponent):
    def __init__(self, conf, system, logger, dsn,
                 kind='pgsql', recursive=False):
        super().__init__(conf, dsn, logger, None)

        self.kind = kind
        self.system = system
        self.recursive = recursive

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
        self.track = Tracking(self.conf, self.system, name)

        if self.recursive:
            self.track.fetch_benchmark_id()
            # change system name in the logs
            self.system = '%s.%s' % (self.system, schedule)

        else:
            self.track.register_benchmark(schedule)
            self.log('starting benchmark %s', self.name)
            self.log('starting schedule %s', schedule)

        # do we know how to do the job?
        if schedule in self.conf.schedules:
            self.schedule = self.conf.schedules[schedule]
        elif schedule in self.conf.jobs:
            # raise the Job into a Schedule: a list of jobs
            self.schedule = [schedule]
        else:
            raise ValueError("schedule not found: %s" % schedule)

        self.start = time.monotonic()

        for phase in self.schedule:

            if not isinstance(phase, list):
                # having ['phase1', 'phase2'] in the logs isn't helpful here
                self.log('starting schedule phase %s', phase)

            if isinstance(phase, list):
                # that's a parallel schedule, create a log queue
                q = logs.create_queue()
                l = logs.start_listener(self.logger, q)

                # start workers
                workers = []
                for p in phase:
                    w = Process(name=p,
                                target=run_sub_schedule,
                                args=(p, q,
                                      self.name,
                                      self.conf,
                                      self.system,
                                      self.dsn,
                                      self.kind))
                    workers.append(w)
                    w.start()

                # wait until workers are done
                for p in phase:
                    w.join()

                # wait until the queue log listener is done, too
                q.put_nowait(None)
                l.join()

            elif phase == 'initdb':
                # The initial phase name is hard-coded
                initdb = InitDB(self.conf, self.dsn, self.schema,
                                self.logger, self.track)
                initdb.run(self.system)

            elif phase in self.conf.jobs:
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

            elif phase in self.conf.schedules:
                # a schedule can be “recursive”, that is defined in terms of
                # other schedules… we lazily walk the tree, which might be a
                # cyclic graph for an infinite loop benchmark
                cmd = Schedule(self.conf, self.system, self.logger, self.dsn,
                               kind=self.kind, recursive=True)
                cmd.run(self.name, phase)

            else:
                raise ValueError("Unknown schedule entry %s", phase)

        self.end = time.monotonic()

        self.track.register_run_time(self.end - self.start)

        if not self.recursive:
            self.log('schedule %s done in %gs', schedule, self.end - self.start)

        return


def run_sub_schedule(schedule, queue, name, conf, system, dsn, kind):
    "Helper function to run parallel sub-schedule jobs."
    logger = logs.get_worker_logger(queue)
    bench = Schedule(conf, system, logger, dsn, kind=kind, recursive=True)
    bench.run(name, schedule)
    return
