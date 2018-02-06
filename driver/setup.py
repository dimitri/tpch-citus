import os
import sys
import json
import time
import boto3
import configparser

from datetime import date, datetime
from collections import namedtuple

EBS_conf = namedtuple('EBS', 'iops size type')
RDS_conf = namedtuple('RDS', 'name iops size iclass stype version')
Aurora_conf = namedtuple('Aurora', 'name iclass stype')

class Setup():
    def __init__(self, filename):
        conf = configparser.ConfigParser()
        conf.read("./ec2.ini")

        self.region  = conf.get('ec2', 'REGION')
        self.az      = conf.get('ec2', 'AZ')
        self.vpc     = conf.get('ec2', 'VPC')
        self.subnet  = conf.get('ec2', 'SUBNET')
        self.sg      = conf.get('ec2', 'SG')
        self.ami     = conf.get('ec2', 'AMI')
        self.keyname = conf.get('ec2', 'KeyName')
        self.itype   = conf.get('ec2', 'INSTANCE')

        self.ebs = EBS_conf(iops = conf.getint('ebs', 'iops'),
                            size = conf.getint('ebs', 'size'),
                            type = conf.get('ebs', 'type'))

        self.rds = RDS_conf(name    = conf.get('rds', 'name'),
                            iops    = conf.getint('rds', 'iops'),
                            size    = conf.getint('rds', 'size'),
                            iclass  = conf.get('rds', 'class'),
                            stype   = conf.get('rds', 'stype'),
                            version = conf.get('rds', 'pgversion'))

        self.aurora = Aurora_conf(
            name    = conf.get('rds', 'name'),
            iclass  = conf.get('rds', 'class'),
            stype   = conf.get('rds', 'stype')
        )
