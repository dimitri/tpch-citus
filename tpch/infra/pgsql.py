import os
import sys
import json
import time
import boto3
import logging
import configparser

from collections import namedtuple

from . import utils
from . import instance
from ..control import utils as cntl

MAKEFILE     = 'Makefile.loader'
GET_IP_ADDR  = 'make -s -C tpch -f %s getipaddr' % MAKEFILE
MAKE_PROV_DB = 'make SBUFS=%%s -C tpch -f %s %%s' % MAKEFILE


class PgSQL(instance.Instance):

    def __init__(self, name, conf, spec, conn, filename = None):
        self.name = name
        self.conf = conf
        self.spec = spec
        self.conn = conn
        self.filename = filename

        if self.filename and os.path.exists(self.filename):
            self.load_json(filename)

        self.log = logging.getLogger('TPCH')

        # for now we only support debian/ubuntu os, with the ubuntu AMI for
        # EC2, so hardcode the username.
        self.username = "ubuntu"

    def run(self):
        # use self.conf for the instance parameters
        # store the EC2 output in self.filename, as JSON

        if self.filename and os.path.exists(self.filename) and self.id:
            return self.id

        self.log.info('%s: Creating an EC2 instance with AMI %s',
                      self.name, self.spec.ami)

        ebs = {
            # 'Encrypted': False,
            'DeleteOnTermination': True,
            'VolumeSize': self.conf.ebs.size,
            'VolumeType': self.conf.ebs.stype
        }

        if self.conf.ebs.stype == 'io1':
            ebs['Iops'] = self.conf.ebs.iops

        out = self.conn.run_instances(
            ImageId = self.spec.ami,
            InstanceType = self.spec.instance,
            KeyName = self.conf.keyname,
            Placement = {'AvailabilityZone':
                         self.conf.az},
            SecurityGroupIds = [self.conf.sg],
            SubnetId = self.conf.subnet,
            BlockDeviceMappings = [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': ebs
                }
            ],
            MinCount = 1,
            MaxCount = 1
        )
        with open(self.filename, 'w') as outfile:
            json.dump(out, outfile, default=utils.json_serial, indent=6)

        # update some internal "cache" from the JSON file just generated
        self.load_json(self.filename)

        # and return the current status of the newly created instance
        return self.id

    def create(self):
        return self.run()

    def delete(self):
        return self.terminate()

    def get_instance_class(self):
        return self.get_instance_type()

    def prepare(self):
        # wait until the loader is properly started and has an IP address
        ip = self.wait_for_public_ip()

        # sync local code and compile our tooling
        self.log.info('%s: rsync tpch repository', self.name)
        cntl.rsync(ip, username=self.username)

        # run a first set of commands on the machine
        command = './tpch/scripts/ubuntu.essentials.sh'
        self.log.info('%s: %s', self.name, command)
        cntl.execute_remote_command(ip, command, username=self.username)

        # run e.g. make -f Makefile.loader deb-pg11
        target = '%s-pg%s' % (self.spec.os, self.spec.pgversion)
        command = MAKE_PROV_DB % (self.spec.sbufs, target)
        self.log.info('%s: %s', self.name, command)
        cntl.execute_remote_command(ip, command, username=self.username)

        return

    def is_ready(self):
        if hasattr(self, "id") and self.id:
            return self.status() == 'running'
        else:
            return False

    def getipaddr(self):
        ip = self.wait_for_public_ip()
        out, err = cntl.execute_remote_command(ip,
                                               GET_IP_ADDR,
                                               username=self.username)
        return out[0]

    def dsn(self):
        host = self.getipaddr()
        dsn = 'postgres://tpch@%s:5432/tpch' % host
        return dsn

