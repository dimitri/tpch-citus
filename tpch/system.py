import os
import os.path
import logging

import boto3

from .infra import setup
from .infra import rds
from .infra import aurora
from .infra import instance
from .infra import utils
from .control import utils as cntl

MAKEFILE      = 'Makefile.loader'
MAKE_OS_TOOLS = 'make -C tpch -f %s os tools' % MAKEFILE
MAKE_RES_DUMP = 'make -C tpch -f %s dump' % MAKEFILE
DUMP_FILES    = ['run.copy', 'job.copy', 'query.copy']

MERGE_RESULTS  = os.path.relpath(
    os.path.join(cntl.TOPDIR, 'scripts', 'merge-results.sh'))
MERGE_RESULTS += ' %s %s %s %s'

RUN_TPCH   = './tpch/tpch.py benchmark %s '
RUN_TPCH  += ' --name %s'
RUN_TPCH  += ' --schedule %s'
RUN_TPCH  += ' --dsn %s'
RUN_TPCH  += ' --kind %s'
RUN_TPCH  += ' --ini tpch.ini'  # we SCP it there at start time
RUN_TPCH  += ' --log tpch.log'  # we create the log file in $HOME too
RUN_TPCH  += ' --detach'


class System():
    def __init__(self, run, name, schedule):
        self.run = run
        self.name = name
        self.schedule = schedule

        awsdir = cntl.awsdir(self.run)
        self.conf = setup.Setup(cntl.infra_ini_path(self.run))

        self.lconn = boto3.client('ec2', self.conf.region)
        self.ljson = os.path.join(awsdir, '%s.loader.json' % name)

        self.dconn = boto3.client('rds', self.conf.region)
        self.djson = None
        if self.name in ('rds', 'aurora'):
            self.djson = os.path.join(awsdir, 'db.%s.json' % name)

        self.get_loader()
        self.get_db()

        self.log = logging.getLogger('TPCH')

        return

    def get_db(self):
        self.db = None
        if self.name == 'rds':
            self.db = rds.RDS(self.conf, self.dconn, self.djson)

        elif self.name == 'aurora':
            self.db = aurora.Aurora(self.conf, self.dconn, self.djson)

        return self.db

    def get_loader(self):
        self.loader = instance.Instance(self.conf, self.lconn, self.ljson)
        return self.loader

    def prepare_loader(self):
        # wait until the loader is properly started and has an IP address
        ip = self.loader.wait_for_public_ip()

        # sync local code and compile our tooling
        self.log.info('%s: rsync tpch repository', self.name)
        cntl.rsync(ip)

        # install os tools:
        self.log.info('%s: setup OS and TPC-H tools', self.name)
        self.log.info(MAKE_OS_TOOLS)
        cntl.execute_remote_command(ip, MAKE_OS_TOOLS)
        return

    def prepare(self):
        # start the database resource on AWS, if any
        if self.name == 'rds':
            self.db = rds.RDS(self.conf, self.dconn, self.djson)
            self.log.info('%s: create db: %s', self.name, self.db.create())

        elif self.name == 'aurora':
            self.db = aurora.Aurora(self.conf, self.dconn, self.djson)
            self.log.info('%s: create db: %s', self.name, self.db.create())

        else:
            # other types (citus, pgsql) are expected to provide a DSN
            pass

        # and create the loader
        lid = self.get_loader().run()
        self.log.info('%s: start loader %s', self.name, lid)

        return

    def dsn(self):
        self.get_db()
        if self.name in ('rds', 'aurora'):
            return self.db.dsn()

        elif self.name == 'pgsql':
            return self.conf.pgsql.dsn

        elif self.name == 'citus':
            return self.conf.citus.dsn

        else:
            raise ValueError("Unknown system name: %s", self.name)

    def has_infra(self):
        return (self.ljson and os.path.exists(self.ljson)) \
            or (self.djson and os.path.exists(self.djson))

    def is_ready(self):
        if self.loader.status() == 'running':
            ip = self.loader.public_ip()

            if self.db:
                # first do the AWS API call, then the ssh:22 ping, to leave
                # some more time to the instance to be ready
                return self.db.status() == 'available' and utils.ping(ip)
            else:
                # we're ready is the loader has an IP already
                return utils.ping(ip)
        else:
            # the loader isn't running yet, we're not ready
            return False

    def tpch_is_running(self):
        if self.is_ready():
            ip = self.loader.public_ip()
            command = "cat /tmp/TPCH.pid"
            out, _ = cntl.execute_remote_command(ip, command, quiet=True)
            try:
                if out and len(out) == 1:
                    pid = int(out[0])
                    return True
            except ValueError:
                # not an integer in that file?!
                return False
            except RuntimeError:
                # e.g. file does not exists
                return False
        return False

    def tail(self, follow=False):
        if self.is_ready():
            ip = self.loader.wait_for_public_ip()

            if follow:
                command = "tail -f tpch.log"
                remote = cntl.BufferedRemoteCommand(ip, command)
                remote.open()

                # return an iterator object
                return iter(remote)

            else:
                command = "tail tpch.log"
                out, _ = cntl.execute_remote_command(ip, command)
                for line in out:
                    print(line)

        return

    def status(self):
        print('%s' % self.name)
        print('%s' % ('-' * len(self.name)))

        lstatus = self.loader.status()
        ip = '-'
        if lstatus == 'running':
            ip = self.loader.public_ip()

        dstatus = '-'
        if self.db:
            dstatus = self.db.status()
        dsn = self.dsn()

        print('  database %15s %s'   % (dstatus, dsn))
        print('    loader %15s %15s' % (lstatus, ip))

    def start(self):
        if self.is_ready():
            self.log.info('%s run benchmark %s', self.name, self.schedule)

            ip = self.loader.public_ip()
            cntl.upload(ip, cntl.tpch_ini_path(self.run), './tpch.ini')

            # FIXME: generalize the INFRA bits so that we can have more than
            # one citus system in the setup, and same with pgsql, rds or
            # aurora SUT.
            self.kind = 'pgsql'
            if self.name == 'citus':
                self.kind = 'citus'

            cmd = RUN_TPCH % (self.name,
                              self.run,
                              self.schedule,
                              self.dsn(),
                              self.kind)
            self.log.info(cmd)
            cntl.execute_remote_command(ip, cmd)

        else:
            self.log.warning('%s is not ready to run any benchmark', self.name)

    def terminate(self):
        self.cancel()

        if self.db and os.path.exists(self.djson):
            self.log.info("%s: deleting database instance", self.name)
            self.db.delete()

        return

    def cancel(self):
        # terminate only the loader
        if os.path.exists(self.ljson):
            self.log.info("%s: terminating loader %s", self.name, self.loader.id)
            print(self.loader.terminate())
        return

    def update(self, resdb):
        if self.loader.status() == 'running':
            ip = self.loader.public_ip()

            self.fetch_logs_and_results(ip)
            self.merge_results(resdb)

        else:
            self.merge_results(resdb)

        return

    def fetch_logs_and_results(self, ip=None):
        if not ip:
            if self.is_ready():
                ip = self.loader.public_ip()
            else:
                self.log.error(
                    "%s: can't fetch logs and results, loader not ready",
                    self.name)
                return

        session = cntl.RemoteSession(ip)
        # fetch logs
        logfile = cntl.logfile(self.run, self.name)
        self.log.info('%s: downloading logs in %s',
                      self.name, os.path.relpath(logfile))

        session.download('tpch.log', logfile)

        # fetch current results
        self.log.info('%s: dumping current results', self.name)
        self.log.info("%s: ssh -l ec2-user %s %s" % (self.name,
                                                     ip,
                                                     MAKE_RES_DUMP))
        session.execute(MAKE_RES_DUMP)

        copy_files = self.list_copy_files()
        resdir = os.path.relpath(cntl.resdir(self.run))

        for src, dest in copy_files.items():
            self.log.info('%s: downloading results in %s',
                          self.name, os.path.relpath(dest))
            session.download(src, dest)

        session.close()
        return

    def merge_results(self, resdb):
        # merge results in local tracking database
        resdir = os.path.relpath(cntl.resdir(self.run))
        command = MERGE_RESULTS % (resdb, self.name, resdir, self.run)

        self.log.info("%s: merging results", self.name)
        self.log.info(command)
        cntl.run_command("Merge Results", command)

        return

    def list_copy_files(self):
        copy_files = {}

        resdir = os.path.relpath(cntl.resdir(self.run))

        for copy in DUMP_FILES:
            # local copy filename
            tab, _ = os.path.splitext(copy)
            lcfn = os.path.join(resdir, '%s.%s.copy' % (self.name, tab))

            copy_files[copy] = lcfn

        return copy_files

    def list_result_files(self):
        files = []

        logfile = cntl.logfile(self.run, self.name)
        files.append(os.path.relpath(logfile))

        copy_files = self.list_copy_files()
        for _, copy in copy_files.items():
            files.append(os.path.relpath(copy))

        return files
