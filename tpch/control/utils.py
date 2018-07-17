import os
import shutil
import os.path
import time
import shlex
import logging
import subprocess
import psycopg2

from pathlib import Path
from itertools import chain, cycle, islice
from paramiko.client import SSHClient, MissingHostKeyPolicy

TOPDIR  = os.path.join(os.path.dirname(__file__), '..', '..')
OUTDIR  = os.path.join(TOPDIR, 'aws.out')

RESDB_SCHEMA = os.path.join(TOPDIR, 'schema', 'tracking.sql')
RESDB_PSQL   = 'psql -X -a -d %%s -f %s' % RESDB_SCHEMA

REMOTE_USER = 'ec2-user'
RSYNC_OPTS  = '--exclude-from "rsync.exclude"'
RSYNC_OPTS += ' -e "ssh -o StrictHostKeyChecking=no"'
RSYNC_OPTS += ' -avz'


def outdir(name):
    outdir = os.path.join(OUTDIR, name)
    os.makedirs(outdir, exist_ok=True)
    return outdir


def resdir(name):
    resdir = os.path.join(outdir(name), 'results')
    os.makedirs(resdir, exist_ok=True)
    return resdir


def logdir(name):
    logdir = os.path.join(outdir(name), 'logs')
    os.makedirs(logdir, exist_ok=True)
    return logdir


def awsdir(name):
    awsdir = os.path.join(outdir(name), 'aws')
    os.makedirs(awsdir, exist_ok=True)
    return awsdir


def setup_out_dir(name, infra, sched):
    od = outdir(name)

    # copy given infra.ini and schedule.ini to our outdir
    shutil.copyfile(infra, os.path.join(od, 'infra.ini'))
    shutil.copyfile(sched, os.path.join(od, 'schedule.ini'))

    return


def list_runs(rdir=OUTDIR):
    p = Path(rdir)
    for f in p.iterdir():
        if f.is_dir() and os.path.exists(os.path.join(f, 'run.ini')):
            yield f.name


def run_ini_path(name, filename='run.ini'):
    return os.path.join(OUTDIR, name, filename)


def infra_ini_path(name, filename='infra.ini'):
    return os.path.join(OUTDIR, name, filename)


def sched_ini_path(name, filename='schedule.ini'):
    return os.path.join(OUTDIR, name, filename)


def logfile(name, prefix):
    filename = '%s.log' % prefix
    return os.path.abspath(os.path.join(logdir(name), filename))


def rsync(ip, verbose=False, username=REMOTE_USER):
    command = 'rsync %s %s/ %s@%s:tpch/' \
              % (RSYNC_OPTS, TOPDIR, username, ip)
    run_command('RSYNC', command)


def upload(ip, src, dst, username=REMOTE_USER):
    command = 'scp %s %s@%s:%s' % (src, username, ip, dst)
    run_command('scp upload', command)


def download(ip, src, dst, username=REMOTE_USER):
    command = 'scp %s@%s:%s %s' % (username, ip, src, dst)
    run_command('scp download', command)


def run_command(name, command):
    cmd = shlex.split(command)

    with subprocess.Popen(cmd,
                          encoding='utf-8',
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as p:
        out, err = p.communicate()
        rc = p.returncode

        if rc != 0:
            log = logging.getLogger('TPCH')

            log.error('Command %s failed with return code %d', name, rc)
            log.error(command)
            print(out)
            print(err)

            raise RuntimeError(name)
        return out.splitlines(), err.splitlines()


class IgnoreHostKeyPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return


def execute_remote_command(ip, command, quiet=False, username=REMOTE_USER):
    client = SSHClient()
    client.set_missing_host_key_policy(IgnoreHostKeyPolicy)
    client.connect(ip, username=username)
    stdin, stdout, stderr = client.exec_command(command)

    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8').splitlines()
    err = stderr.read().decode('utf-8').splitlines()

    client.close()

    if rc != 0 and not quiet:
        log = logging.getLogger('TPCH')

        log.error("ssh command returned %d" % rc)
        log.error("ssh -l %s %s %s" % (username, ip, command))
        print(command)
        for line in out:
            print(line)
        for line in err:
            print(line)
        print()

    return out, err


class RemoteSession():
    def __init__(self, ip, username=REMOTE_USER):
        self.username = username

        self.client = SSHClient()
        self.client.set_missing_host_key_policy(IgnoreHostKeyPolicy)
        self.client.connect(ip, username=self.username)

        self.sftp = self.client.open_sftp()


    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)

        rc = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8').splitlines()
        err = stderr.read().decode('utf-8').splitlines()

        if rc != 0 and not quiet:
            log = logging.getLogger('TPCH')

            log.error("ssh command returned %d" % rc)
            log.error("ssh -l %s %s %s" % (self.username, ip, command))
            print(command)
            for line in out:
                print(line)
            for line in err:
                print(line)
            print()

        return

    def download(self, src, dst):
        self.sftp.get(src, dst)
        return

    def close(self):
        self.client.close()


class BufferedRemoteCommand():
    def __init__(self, ip, command, username=REMOTE_USER):
        self.ip = ip
        self.command = command
        self.username = username

        self.client = SSHClient()
        self.client.set_missing_host_key_policy(IgnoreHostKeyPolicy)

        self.lines = []
        self.current_line = None
        return

    def open(self):
        self.client.connect(self.ip, username=self.username)

        self.transport = self.client.get_transport()
        self.transport.set_keepalive(30)

        self.channel = self.transport.open_session()
        self.channel.set_combine_stderr(True)

        self.channel.exec_command(self.command)

        return

    def read(self, nbytes=256):
        if self.channel.recv_ready():
            b = self.channel.recv(nbytes)

            if len(b) == 0:
                self.closed = True
                return 0, None
            else:
                s = b.decode('utf-8')
                return len(b), s

        # try again later
        return -1, None

    def readlines(self):
        nbytes, out = self.read()

        if nbytes == -1:
            # no luck this time, come later
            while nbytes == -1:
                time.sleep(1)
                nbytes, out = self.read()

        if nbytes == 0:
            # we're closed
            lines = []

        else:
            lines = out.splitlines()

            if self.current_line:
                lines[0] = self.current_line + lines[0]
                self.current_line = None

            if out[-1] != '\n':
                self.current_line = lines[-1]
                lines = lines[:-1]

            if not lines:
                # we got a chunk of a line, not a whole one, keep buffering
                return self.readlines()

        return nbytes, lines

    def __iter__(self):
        return self

    def __next__(self):
        if self.channel.exit_status_ready():
            self.rc = self.channel.recv_exit_status()
            raise StopIteration

        if not self.lines:
            # fetch another round on the remote connection
            nbytes, self.lines = self.readlines()

            if nbytes == 0:
                # we're done
                raise StopIteration

        line = self.lines.pop(0)
        return line

    def close(self):
        return self.client.close()


def roundrobin(iterables, startup=10):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    lines = {}
    for it in iterables:
        lines[it] = 0

    for it in iterables:
        while lines[it] < startup:
            yield it.__next__()
            lines[it] += 1

    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def maybe_install_resdb(resdb):
    conn = psycopg2.connect(resdb)

    sql = """
select count(*)
  from pg_class
 where relname in ('run',
                   'job',
                   'query',
                   'results',
                   'qpm',
                   'query_timings')
"""
    curs = conn.cursor()
    curs.execute(sql)
    count, = curs.fetchone()

    if count != 6:
        log = logging.getLogger('TPCH')
        log.info("Installing the tracking schema in %s", resdb)
        run_command('tracking.sql', RESDB_PSQL % resdb)

    return
