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

    def tail(self, follow=False):
        ip = self.loader.wait_for_public_ip()
        command = "tail tpch.log"
        if follow:
            command = "tail -f tpch.log"

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

        if self.db:
            self.log.info("%s: deleting database instance", self.name)
            self.db.delete()

        self.status()
        return

    def cancel(self):
        # terminate only the loader
        self.log.info("%s: terminating loader %s", self.name, self.loader.id)
        print(self.loader.terminate())
        return

    def update(self, resdb):
        if self.is_ready():
            ip = self.loader.public_ip()

            # fetch logs
            logfile = cntl.logfile(self.run, self.name)
            self.log.info('%s: downloading logs in %s',
                          self.name, os.path.relpath(logfile))
            cntl.download(ip, 'tpch.log', logfile)

            # fetch current results
            self.log.info('%s: dumping and fetching current results',
                          self.name)
            self.log.info(MAKE_RES_DUMP)
            cntl.execute_remote_command(ip, MAKE_RES_DUMP)

            resdir = os.path.relpath(cntl.resdir(self.run))

            for copy in DUMP_FILES:
                # local copy filename
                tab, _ = os.path.splitext(copy)
                lcfn = os.path.join(resdir, '%s.%s.copy' % (self.name, tab))
                self.log.info('%s: downloading results in %s',
                              self.name,
                              os.path.relpath(lcfn))
                cntl.download(ip, copy, lcfn)

            # merge results in local tracking database
            command = MERGE_RESULTS % (resdb, self.name, resdir, self.run)
            self.log.info("%s: merging results", self.name)
            self.log.info(command)
            cntl.run_command("Merge Results", command)

        return
