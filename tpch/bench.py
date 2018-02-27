import os
import os.path
import logging
import psycopg2
import humanize

from . import system
from .control import setup
from .control import utils
from .run import setup as tpch

RUNFILE = 'run.ini'
CLEAN_RESULTS  = 'psql -a -d %s -v run=%s -f '
CLEAN_RESULTS += os.path.relpath(
    os.path.join(utils.TOPDIR, 'schema', 'tracking-delete-run.sql'))


class Run():
    def __init__(self, name, only_system=None):
        self.name = name

        self.cfn  = os.path.join(utils.outdir(name), RUNFILE)
        self.conf = setup.Setup(self.cfn)
        self.tpch = tpch.Setup(utils.tpch_ini_path(self.name))

        self.log = logging.getLogger('TPCH')

        if self.conf.run:
            self.schedule = self.conf.run.schedule
            self.sysnames = self.conf.run.systems

            self.systems = [system.System(self.name, sname, self.schedule)
                            for sname in self.sysnames]
        else:
            self.systems = []

        # maybe target only a single given system
        if only_system:
            s = [s for s in self.systems if s.name == only_system]
            if len(s) == 1:
                self.systems = s
            else:
                self.log.error(
                    "System name not found or not unique: %s", only_system)
                self.systems = []

        # and the result database
        self.resdb = self.tpch.results.dsn

    def register(self, systems, schedule):
        self.sysnames = systems
        self.schedule = schedule

        self.conf.create(self.schedule, self.sysnames)
        self.check_config()

    def check_config(self):
        # for now systems are hard-coded, see infra/setup.py
        for s in self.sysnames:
            if s not in ('rds', 'aurora', 'citus', 'pgsql'):
                raise ValueError("Unknown system to test: %s", s)

        if self.schedule not in self.tpch.schedules and \
           self.schedule not in self.tpch.jobs:
            raise ValueError("Unknown benchmark schedule/job %s",
                             self.schedule)

    def prepare(self, schedule):
        if schedule:
            self.schedule = schedule

        self.log.info('%s: preparing the infra' % self.name)
        for s in self.systems:
            self.log.info('%s: preparing system %s' % (self.name, s.name))
            s.prepare()

        # wait until all sytems are ready, to start tests roughly
        self.log.info('%s: waiting for infra services to be ready' % self.name)
        for s in self.systems:
            s.prepare_loader()

        wait = set(self.systems)
        while wait:
            # avoid looping over the wait set object, which we are modifying
            # within the loop we expect 1..4 systems here anyway
            for s in self.systems:
                if s in wait and s.is_ready():
                    wait.remove(s)

    def start(self, schedule):
        # now run the benchmarks on all systems in parallel
        if schedule:
            self.schedule = schedule

        for s in self.systems:
            self.log.info('%s: starting benchmark schedule "%s" on system %s'
                          % (self.name, self.schedule, s.name))
            s.start()

        return

    def progress(self):
        sql = """
with ten as (
     select system, job, job_number, duration, steps, count
       from results
      where run = %s
   order by job_number, system
)
 select * from ten order by job_number, system;
"""
        conn = psycopg2.connect(self.resdb)
        curs = conn.cursor()

        curs.execute(sql, (self.name,))

        print("%10s | %25s | %2s | %12s | %8s | %5s"
              % ("System", "Job", "#", "Duration", "Steps", "Qs"))

        print("%10s-|-%25s-|-%2s-|-%12s-|-%8s-|-%5s"
              % ("-" * 10, "-" * 25, "-" * 2, "-" * 12, "-" * 8, "-" * 5))

        for sysname, job, jobn, secs, steps, count in curs.fetchall():
            if not steps:
                steps = ""

            print("%10s | %25s | %2s | %12s | %8s | %5s"
                  % (sysname, job, jobn,
                     humanize.naturaldelta(secs), steps, count))
        return

    def status(self):
        print(self.name)
        print('config:   %s' % os.path.relpath(self.cfn))
        print('schedule: %s' % self.schedule)
        print('systems:  %s' % (' '.join([s.name for s in self.systems])))
        print()
        for s in self.systems:
            s.status()
            print()

        for s in self.systems:
            if s.loader.status() == 'running':
                print("ssh -l ec2-user %s tail tpch.log" % s.loader.public_ip())
                s.tail()
                print()

        print("Last known progress. Refresh with: ./control.py update %s"
              % self.name)
        print()
        self.progress()
        print()
        return

    def list(self):
        running = [x for x in self.systems if x.loader.status() == 'running']

        if running:
            print("%s currently has %s systems registered, %s running"
                  % (self.name, len(self.systems), len(running)))
        else:
            print("%s is not currently running" % self.name)

        if running:
            specs = self.tpch.schedules[self.schedule] or \
                    self.tpch.jobs[self.schedule]

            scale = self.tpch.scale

            print(" SF %d with %d steps of %s each, total %s"
                  % (scale.factor, scale.children,
                     humanize.naturalsize(scale.factor / scale.children * 10**9),
                     humanize.naturalsize(scale.factor * 10**9)))

            print(" running schedule '%s': %s"
                  % (self.schedule, ', '.join(specs)))

            sql = """
         select system,
                max(job_number) as current_job_number,
                max(job) as current_job,
                sum(duration) as total_duration,
                max(steps) filter(where steps is not null) as step,
                sum(count) filter(where count > 1) as queries
           from results
          where run = %s
       group by system
       order by max(job_number) desc;
    """
            conn = psycopg2.connect(self.resdb)
            curs = conn.cursor()

            curs.execute(sql, (self.name,))
            for system, job_n, job, duration, step, queries in curs.fetchall():
                print("%10s[%s]: stage %s/%s in %s with %s queries "
                      % (system,
                         step.split('..')[1],
                         job_n,
                         job,
                         humanize.naturaldelta(duration),
                         queries))

        return

    def tail(self, follow=True):
        self.log.info("tail %s logs" % (self.name))

        if follow:
            tails = utils.roundrobin([s.tail(True) for s in self.systems])
            for line in tails:
                print(line)

        else:
            for s in self.systems:
                s.tail()

    def update(self, progress=True):
        self.log.info("update %s logs and results", self.name)

        command = CLEAN_RESULTS % (self.resdb, self.name)
        self.log.info("Clean-up previous round of results first…")
        self.log.info(command)
        utils.run_command('Clean-up', command)

        for s in self.systems:
            s.update(self.resdb)

        print()
        for s in self.systems:
            log = utils.logfile(self.name, s.name)
            out, _ = utils.run_command('tail', 'tail -n 3 %s' % log)

            for line in out:
                print(line)

        print()
        if progress:
            self.progress()
        return

    def cancel(self, system=None):
        self.log.info("Cancelling loaders for %s", self.name)
        for s in self.systems:
            s.cancel()

    def terminate(self):
        self.log.info("Terminating the whole infra for %s", self.name)
        for s in self.systems:
            s.terminate()
