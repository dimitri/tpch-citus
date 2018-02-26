import os
import sys
import json
import time
import boto3
import configparser

from datetime import date, datetime
from collections import namedtuple


class Volume():
    def __init__(self, conf, conn, filename):
        self.conf = conf
        self.conn = conn
        self.filename = filename

        if os.path.exists(self.filename):
            self.load_json(filename)
        else:
            print("Creating an EBS resource")

    def create(self):
        out = conn.create_volume(
            AvailabilityZone = self.conf.az,
            Encrypted = False,
            Iops = self.conf.ebs.iops,
            Size = self.conf.ebs.size,
            VolumeType = self.conf.ebs.type
        )
        with open(self.filename, 'w') as outfile:
            json.dump(out, outfile, default=json_serial, indent=6)

        self.load_json(self.filename)

    def load_json(self, filename):
        with open(filename, 'r') as f:
            self.data = json.load(f)

        self.id = self.data["Instances"][0]["InstanceId"]
        return self.data
