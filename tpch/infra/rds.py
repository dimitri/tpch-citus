import os
import sys
import json
import time
import boto3
import configparser

from collections import namedtuple

from . import utils


class RDS():
    def __init__(self, conf, conn, filename = None):
        self.conf = conf
        self.conn = conn
        self.filename = filename

        if self.filename and os.path.exists(self.filename):
            self.load_json(filename)

    def create(self):
        if self.filename and os.path.exists(self.filename) and self.id:
            return self.id

        out = self.conn.create_db_instance(
            DBName = self.conf.rds.dbname,
            DBInstanceIdentifier = self.conf.rds.iname,
            AllocatedStorage = self.conf.rds.size,
            Engine = 'postgres',
            DBInstanceClass = self.conf.rds.iclass,
            MasterUsername = 'tpch',
            MasterUserPassword = 'tcph-dummy-password',
            VpcSecurityGroupIds = [self.conf.sg],
            AvailabilityZone = self.conf.az,
            EngineVersion = self.conf.rds.version,
            StorageType = self.conf.rds.stype,
            Iops = self.conf.rds.iops
        )
        with open(self.filename, 'w') as outfile:
            json.dump(out, outfile, default=utils.json_serial, indent=6)

        # update some internal "cache" from the JSON file just generated
        self.load_json(self.filename)

        # and return the current status of the newly created instance
        return self.id

    def load_json(self, filename):
        with open(filename, 'r') as f:
            self.data = json.load(f)

        self.id = self.data['DBInstance']['DBInstanceIdentifier']
        return self.data

    def describe(self):
        if self.id:
            return self.conn.describe_db_instances(
                DBInstanceIdentifier = self.id)

    def status(self):
        if self.id:
            try:
                desc = self.describe()
                return desc['DBInstances'][0]['DBInstanceStatus']
            except self.conn.exceptions.DBInstanceNotFoundFault:
                return 'Not Found'

    def get_instance_class(self):
        if hasattr(self, "data"):
            return self.data['DBInstance']['DBInstanceClass']
        return None

    def dsn(self):
        desc = self.describe()
        status = desc['DBInstances'][0]['DBInstanceStatus']

        if status == 'available':
            return "postgresql://%s:%s@%s:%s/%s" % (
                desc['DBInstances'][0]['MasterUsername'],
                'tcph-dummy-password',
                desc['DBInstances'][0]['Endpoint']['Address'],
                desc['DBInstances'][0]['Endpoint']['Port'],
                desc['DBInstances'][0]['DBName']
            )
        else:
            return 'No DSN yet: %s' % status

    def wait_for_dsn(self):
        dsn = self.dsn()

        while dsn.startswith(u'No DSN yet:'):
            time.sleep(30)      # creating an RDS instance takes a long time!
            dsn = self.dsn()

        return dsn

    def start(self):
        res = self.conn.start_db_instance(DBInstanceIdentifier = self.id)
        return res['DBInstance']['DBInstanceStatus']

    def stop(self):
        res = self.conn.stop_db_instance(DBInstanceIdentifier = self.id)
        return res['DBInstance']['DBInstanceStatus']

    def delete(self):
        res = self.conn.delete_db_instance(
            DBInstanceIdentifier = self.id,
            SkipFinalSnapshot = True
        )
        if self.filename and os.path.exists(self.filename):
            os.remove(self.filename)
        return res['DBInstance']['DBInstanceStatus']
