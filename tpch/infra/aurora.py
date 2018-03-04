import os
import sys
import json
import time
import boto3
import configparser

from collections import namedtuple

from . import rds
from . import utils


class Cluster():

    def __init__(self, az, sg, conf, conn, filename):
        self.az = az
        self.sg = sg
        self.conf = conf
        self.conn = conn
        self.filename = filename

        if self.filename and os.path.exists(self.filename):
            self.load_json(filename)

        # Some Hard Coded values, currently not intended to be specified in
        # the INI file setup
        self.Port = 5432
        self.MasterUsername = 'tpch'
        self.MasterUserPassword = 'tcph-dummy-password'

    def create(self):
        if self.filename and os.path.exists(self.filename) and self.id:
            return self.id

        out = self.conn.create_db_cluster(
            AvailabilityZones = [self.az],
            DatabaseName = self.conf.dbname,
            DBClusterIdentifier = self.conf.cluster,
            VpcSecurityGroupIds = [self.sg],
            Engine = 'aurora-postgresql',
            Port = self.Port,
            MasterUsername = self.MasterUsername,
            MasterUserPassword = self.MasterUserPassword
        )
        with open(self.filename, 'w') as outfile:
            json.dump(out, outfile, default=utils.json_serial, indent=6)

        # update some internal "cache" from the JSON file just generated
        self.load_json(self.filename)

        # and return the id of the newly created cluster
        return self.id

    def load_json(self, filename):
        with open(filename, 'r') as f:
            self.data = json.load(f)

        self.id = self.data['DBCluster']['DBClusterIdentifier']
        return self.data

    def describe(self):
        if self.id:
            return self.conn.describe_db_clusters(
                DBClusterIdentifier = self.id)

    def status(self):
        if self.id:
            try:
                self.data = self.conn.describe_db_clusters(
                    DBClusterIdentifier = self.id)
                return self.data['DBClusters'][0]['Status']
            except self.conn.exceptions.DBClusterNotFoundFault:
                return 'Not Found'

    def endpoint(self):
        if self.id:
            desc = self.describe()
            return desc['DBClusters'][0]['Endpoint']

    def delete(self):
        res = self.conn.delete_db_cluster(
            DBClusterIdentifier = self.id,
            SkipFinalSnapshot = True
        )
        if self.filename and os.path.exists(self.filename):
            os.remove(self.filename)

        return res['DBCluster']['Status']


class Aurora(rds.RDS):

    def __init__(self, az, sg, conf, conn, filename = None):
        self.az = az
        self.sg = sg
        self.conf = conf
        self.conn = conn
        self.filename = filename

        if self.filename and os.path.exists(self.filename):
            self.load_json(filename)

        if self.filename:
            name, extension = os.path.splitext(self.filename)
            cluster_filename = '%s.cluster.%s' % (name, extension[1:])
            self.cluster = Cluster(az, sg, conf, conn, cluster_filename)

    def create(self):
        if self.filename and os.path.exists(self.filename) and self.id:
            return self.id

        # first create a Cluster, if needed
        self.cluster.create()

        out = self.conn.create_db_instance(
            DBClusterIdentifier = self.cluster.id,
            DBInstanceIdentifier = self.conf.iname,
            Engine = 'aurora-postgresql',
            DBInstanceClass = self.conf.iclass
        )
        with open(self.filename, 'w') as outfile:
            json.dump(out, outfile, default=utils.json_serial, indent=6)

        # update some internal "cache" from the JSON file just generated
        self.load_json(self.filename)

        # and return the current status of the newly created instance
        return self.id

    def dsn(self):
        if self.cluster.status() == 'available':
            return "postgresql://%s:%s@%s:%s/%s" % (
                self.cluster.MasterUsername,
                self.cluster.MasterUserPassword,
                self.cluster.endpoint(),
                self.cluster.Port,
                self.conf.dbname
            )

    def delete(self):
        instance_ret = self.conn.delete_db_instance(
            DBInstanceIdentifier = self.id,
            SkipFinalSnapshot = True
        )
        if self.filename and os.path.exists(self.filename):
            os.remove(self.filename)

        cluster_status = self.cluster.delete()

        return cluster_status, instance_ret['DBInstance']['DBInstanceStatus']
