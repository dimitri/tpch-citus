import os
import os.path
import logging
import psycopg2
import humanize

from . import system
from .control import setup
from .control import utils
from .run import setup as sched
from .infra import setup as infra

RUNFILE = 'run.ini'
CLEAN_RESULTS  = 'psql -a -d %s -v run=%s -f '
CLEAN_RESULTS += os.path.relpath(
    os.path.join(utils.TOPDIR, 'schema', 'tracking-delete-run.sql'))


class Run():
    def __init__(self, name, only_system=None, resdb=None):
        self.name = name

        self.cfn  = os.path.join(utils.outdir(name), RUNFILE)
        self.conf = setup.Setup(self.cfn)
        self.sched = sched.Setup(utils.sched_ini_path(self.name))
        self.infra = infra.Setup(utils.infra_ini_path(self.name))

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
        if resdb:
            self.resdb = resdb
        else:
            self.resdb = self.sched.results.dsn

    def register(self, schedule, systems):
        self.schedule = schedule

        if systems:
            self.sysnames = systems
        else:
            self.sysnames = [name for name in self.infra.infra]

        self.conf.create(self.schedule, self.sysnames)
        self.check_config()

    def check_config(self):
        # for now systems are hard-coded, see infra/setup.py
        for s in self.sysnames:
            if s not in self.infra.infra:
                raise ValueError("Unknown system to test: %s", s)

        if self.schedule not in self.sched.schedules and \
           self.schedule not in self.sched.jobs:
            raise ValueError("Unknown benchmark schedule/job %s",
                             self.schedule)

    def has_infra(self):
        return any([s.has_infra() for s in self.systems])

    def list_infra(self, with_dsn=False):
        if not self.has_infra():
            return

        print()
        print("Infra for benchmark %s:" % self.name)
        print()
        print("%20s | %20s | %15s | %15s | %15s"
              % ("Resource", "AWS Id", "Type", "Status", "Address"))
        print("%20s-|-%20s-|-%15s-|-%15s-|-%15s"
              % ("-" * 20, "-" * 20, "-" * 15, "-" * 15, "-" * 15))

        for s in self.systems:
            if os.path.exists(s.ljson):
                loader = s.get_loader()
                print("%20s | %20s | %15s | %15s | %15s"
                      % ("%s loader" % s.name,
                         loader.id,
                         loader.get_instance_type(),
                         loader.status(),
                         loader.public_ip()))

        db_dsn = {}
        for s in self.systems:
            dbinfo = s.get_db_info()
            if dbinfo:
                db_dsn[dbinfo.label] = dbinfo.dsn

            if dbinfo and s.manage_db():
                if s.get_db_type() == 'PgSQL':
                    print("%20s | %20s | %15s | %15s | %15s" %
                          (dbinfo.label, dbinfo.id, dbinfo.iclass, dbinfo.status,
                           s.get_db().public_ip()))
                else:
                    print("%20s | %20s | %15s | %15s |" % (dbinfo.label,
                                                           dbinfo.id,
                                                           dbinfo.iclass,
                                                           dbinfo.status))

        if with_dsn:
            print()
            print("Database Connection Strings")
            for name, dsn in db_dsn.items():
                print("%9s: %s" % (name, dsn))

        return

    def prepare(self):
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

    def results(self, verbose=False):
        if verbose:
            print("Results for benchmark %s:" % self.name)
            self.print_specs()

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

    def status(self, with_results=True):
        self.list()
        print()
        self.list_infra()
        print()
        self.tail()
        print()

        if with_results:
            self.results()
            print()

        return

    def tpch_is_running(self):
        return any([s.tpch_is_running() for s in self.systems])

    def print_specs(self):
        # two lines because of pycodestyle policies
        specs = self.sched.schedules[self.schedule]
        specs = specs or self.sched.jobs[self.schedule]
        stages = self.sched.stages(self.schedule)

        scale = self.sched.scale

        print(" SF %d with %d steps of %s each, total %s"
              % (scale.factor, scale.children,
                 humanize.naturalsize(scale.factor / scale.children * 10**9),
                 humanize.naturalsize(scale.factor * 10**9)))

        print(" schedule %s[%s stages]: %s"
              % (self.schedule, stages, ', '.join(specs)))

        return stages

    def list(self):
        try:
            running = [s for s in self.systems if s.tpch_is_running()]
        except Exception:
            running = []

        if running:
            warn = ""
            if len(running) != len(self.systems):
                warn = "!"
            print("%s currently has %s systems registered, %s running%s"
                  % (self.name, len(self.systems), len(running), warn))
        else:
            print("%s ran with %s systems registered"
                  % (self.name, len(self.systems)))

        stages = self.print_specs()

        sql = """
     select system,
            max(job_number) as current_job_number,
            (
              array_agg(job order by job_number)
            )[max(job_number)] as current_job,
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
            current_step = ""
            if step:
                current_step = int(step.split('..')[1])
                current_step = int(current_step
                                   * self.sched.scale.factor
                                   / self.sched.scale.children)

            print("%10s[%2s]: stage %s/%s (%s) in %s with %s queries "
                  % (system,
                     current_step,
                     job_n,
                     stages,
                     job,
                     humanize.naturaldelta(duration),
                     queries))

        return

    def tail(self, follow=False, n=10):
        self.log.info("tail %s logs" % (self.name))

        if follow:
            tails = utils.roundrobin([s.tail(True)
                                      for s in self.systems
                                      if s.is_ready()],
                                     n)
            for line in tails:
                print(line)

        else:
            for s in self.systems:
                s.tail(n=n)
                print()

    def is_ready(self):
        ready = [s.is_ready() for s in self.systems]
        return any(ready)

    def update(self, tail=True, results=True):
        if not self.is_ready():
            return

        self.log.info("update %s logs and results", self.name)

        command = CLEAN_RESULTS % (self.resdb, self.name)
        self.log.info("Clean-up previous round of results first…")
        self.log.info(command)
        utils.run_command('Clean-up', command)

        for s in self.systems:
                s.update(self.resdb)

        if tail:
            for s in self.systems:
                log = utils.logfile(self.name, s.name)
                out, _ = utils.run_command('tail', 'tail -n 3 %s' % log)

                print()
                for line in out:
                    print(line)

        if results:
            print()
            self.results()

        return

    def merge_results(self):
        self.log.info("Merging results for %s", self.name)
        for s in self.systems:
            s.merge_results(self.resdb)

    def cancel(self, system=None):
        self.log.info("Cancelling loaders for %s", self.name)
        for s in self.systems:
            s.cancel()

    def terminate(self):
        self.log.info("Terminating the whole infra for %s", self.name)
        for s in self.systems:
            s.terminate()

        self.list_infra()
        return

    def list_result_files(self):
        files = []

        bench_ini_files = [utils.run_ini_path(self.name),
                           utils.sched_ini_path(self.name),
                           utils.infra_ini_path(self.name)]

        for ini in bench_ini_files:
            relpath = os.path.relpath(ini)
            files.append(relpath)

        for s in self.systems:
            files += s.list_result_files()

        return files
