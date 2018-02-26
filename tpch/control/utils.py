import os
import shutil
import os.path
import shlex
import logging
import subprocess

from paramiko.client import SSHClient, MissingHostKeyPolicy

TOPDIR  = os.path.join(os.path.dirname(__file__), '..', '..')
OUTDIR  = os.path.join(TOPDIR, 'aws.out')

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


def setup_out_dir(name, infra, config):
    outdir = outdir(name)

    # copy given infra.ini and tpch.ini to our outdir
    shutil.copyfile(infra, os.path.join(outdir, 'infra.ini'))
    shutil.copyfile(config, os.path.join(outdir, 'tpch.ini'))

    return


def infra_ini_path(name, filename='infra.ini'):
    return os.path.join(OUTDIR, name, filename)


def tpch_ini_path(name, filename='tpch.ini'):
    return os.path.join(OUTDIR, name, filename)


def logfile(name, prefix):
    filename = '%s.log' % prefix
    return os.path.abspath(os.path.join(logdir(name), filename))


def rsync(ip, verbose=False):
    command = 'rsync %s %s/ %s@%s:tpch/' \
              % (RSYNC_OPTS, TOPDIR, REMOTE_USER, ip)
    run_command('RSYNC', command)


def upload(ip, src, dst):
    command = 'scp %s %s@%s:%s' % (src, REMOTE_USER, ip, dst)
    run_command('scp upload', command)


def download(ip, src, dst):
    command = 'scp %s@%s:%s %s' % (REMOTE_USER, ip, src, dst)
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


def execute_remote_command(ip, command):
    client = SSHClient()
    client.set_missing_host_key_policy(IgnoreHostKeyPolicy)
    client.connect(ip, username=REMOTE_USER)
    stdin, stdout, stderr = client.exec_command(command)

    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8').splitlines()
    err = stderr.read().decode('utf-8').splitlines()

    client.close()

    if rc != 0:
        log = logging.getLogger('TPCH')

        log.error("ssh command returned %d" % rc)
        log.error("ssh -l %s %s %s" % (REMOTE_USER, ip, command))
        print(command)
        for line in out:
            print(line)
        for line in err:
            print(line)
        print()

    return out, err
