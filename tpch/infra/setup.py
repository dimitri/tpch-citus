import os
import sys
import json
import time
import boto3
import configparser

from datetime import date, datetime
from collections import namedtuple

DEFAULT_SHARED_BUFFERS = '4GB'

Loader_conf = namedtuple('EC2', 'instance ami os')
EBS_conf    = namedtuple('EBS', 'iops size stype')
RDS_conf    = namedtuple('RDS',
                         'label iname dbname iops size iclass stype version')
Aurora_conf = namedtuple('Aurora', 'label cluster iname dbname iclass stype')
PgSQL_conf  = namedtuple('PgSQL', 'label ami os instance pgversion sbufs')
Citus_conf  = namedtuple('Citus', 'label dsn')


class Setup():
    def __init__(self, filename):
        conf = configparser.ConfigParser()
        conf.read(filename)

        self.region  = conf.get('aws', 'REGION')
        self.az      = conf.get('aws', 'AZ')
        self.vpc     = conf.get('aws', 'VPC')
        self.subnet  = conf.get('aws', 'SUBNET')
        self.sg      = conf.get('aws', 'SG')
        self.keyname = conf.get('aws', 'KeyName')

        self.ebs = None
        if conf.has_section('ebs'):
            self.ebs = EBS_conf(
                iops      = conf.getint('ebs', 'iops'),
                size      = conf.getint('ebs', 'size'),
                stype     = conf.get('ebs', 'stype')
            )

        self.loader = Loader_conf(
            instance  = conf.get('loader', 'instance'),
            ami       = conf.get('loader', 'ami'),
            os        = conf.get('loader', 'os')
        )

        self.infra = {}

        for section in conf.sections():
            stype = None

            if conf.has_option(section, 'type'):
                stype = conf.get(section, 'type')

            # Backwards compatiblity again
            elif section in ('rds', 'aurora', 'citus', 'pgsql'):
                stype = section

            if stype == 'rds':
                self.infra[section] = self.read_rds(conf, section)

            elif stype == 'aurora':
                self.infra[section] = self.read_aurora(conf, section)

            elif stype == 'citus':
                self.infra[section] = self.read_citus(conf, section)

            elif stype == 'pgsql':
                self.infra[section] = self.read_pgsql(conf, section)

            else:
                # ignore sections with no type here, like [aws], [loader]
                pass

        # maintain compat' with previous versions of the code, where only 4
        # system could be used in infra.ini and they had to be named in the
        # following hard-coded way:
        if 'rds' in self.infra:
            self.rds = self.infra['rds']

        if 'aurora' in self.infra:
            self.aurora = self.infra['aurora']

        if 'citus' in self.infra:
            self.citus = self.infra['citus']

        if 'pgsql' in self.infra:
            self.pgsql = self.infra['pgsql']

        return

    def get_label(self, conf, section):
        label = section
        if conf.has_option(section, 'label'):
            label = conf.get(section, 'label')
        return label

    def read_rds(self, conf, section):
        # backwards compatibility, to be killed
        rds_iname = 'tpch-rds'
        if conf.has_option(section, 'iname'):
            rds_iname = conf.get(section, 'iname')

        rds = RDS_conf(
            label   = self.get_label(conf, section),
            iname   = rds_iname,
            dbname  = conf.get(section, 'dbname'),
            iops    = conf.getint(section, 'iops'),
            size    = conf.getint(section, 'size'),
            iclass  = conf.get(section, 'class'),
            stype   = conf.get(section, 'stype'),
            version = conf.get(section, 'pgversion')
        )
        return rds

    def read_aurora(self, conf, section):
        aurora = Aurora_conf(
            label   = self.get_label(conf, section),
            cluster = conf.get(section, 'cluster'),
            iname   = conf.get(section, 'iname'),
            dbname  = conf.get(section, 'dbname'),
            iclass  = conf.get(section, 'class'),
            stype   = conf.get(section, 'stype')
        )
        return aurora

    def read_citus(self, conf, section):
        citus = Citus_conf(
            label = self.get_label(conf, section),
            dsn   = conf.get(section, 'dsn')
        )
        return citus

    def read_pgsql(self, conf, section):
        sbufs = DEFAULT_SHARED_BUFFERS
        if conf.has_option(section, 'shared_buffers'):
            sbufs = conf.get(section, 'shared_buffers')

        pgsql = PgSQL_conf(
            label = self.get_label(conf, section),
            instance  = conf.get(section, 'instance'),
            ami       = conf.get(section, 'ami'),
            os        = conf.get(section, 'os'),
            pgversion = conf.get(section, 'pgversion'),
            sbufs     = sbufs
        )

        return pgsql
