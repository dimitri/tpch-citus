import os
import sys
import json
import time
import boto3
import botocore
import configparser

from collections import namedtuple

from . import utils


class Instance():
    def __init__(self, conf, conn, filename = None):
        self.conf = conf
        self.conn = conn
        self.filename = filename

        if self.filename and os.path.exists(self.filename):
            self.load_json(filename)

    def run(self):
        # use self.conf for the instance parameters
        # store the EC2 output in self.filename, as JSON

        if self.filename and os.path.exists(self.filename) and self.id:
            return self.id

        ebs = {
            # 'Encrypted': False,
            'DeleteOnTermination': True,
            'VolumeSize': self.conf.ebs.size,
            'VolumeType': self.conf.ebs.stype
        }

        if self.conf.ebs.stype == 'io1':
            ebs['Iops'] = self.conf.ebs.iops

        out = self.conn.run_instances(
            ImageId = self.conf.loader.ami,
            InstanceType = self.conf.loader.instance,
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

    def load_json(self, filename):
        with open(filename, 'r') as f:
            self.data = json.load(f)

        self.id = self.data["Instances"][0]["InstanceId"]
        return self.data

    def get_instance_id(self):
        return self.data["Instances"][0]["InstanceId"]

    def get_instance_type(self):
        if hasattr(self, "id"):
            return self.data["Instances"][0]["InstanceType"]
        return None

    def status(self):
        if hasattr(self, "id"):
            try:
                self._status = self.conn.describe_instance_status(
                    InstanceIds = [self.id])
            except botocore.exceptions.ClientError:
                return "unknown"
        else:
            return "unknown"

        if self._status["InstanceStatuses"]:
            return self._status["InstanceStatuses"][0]["InstanceState"]["Name"]
        else:
            return "Unknown"

    def public_ip(self):
        filter = {'Name': 'attachment.instance-id', 'Values': [self.id]}
        nic = self.conn.describe_network_interfaces(Filters = [filter])
        self.interfaces = nic
        if nic["NetworkInterfaces"]:
            return nic["NetworkInterfaces"][0]["Association"]["PublicIp"]

    def wait_for_public_ip(self):
        status = self.status()

        while status != 'running':
            time.sleep(1)
            status = self.status()

        # ok it's running, what about actually listening to ssh connections?
        ip = self.public_ip()
        utils.wait_for_service(ip, port=22)

        return ip

    def start(self):
        res = self.conn.start_instances(InstanceIds = [self.id])
        return res

    def stop(self):
        res = self.conn.stop_instances(InstanceIds = [self.id])
        return res['StoppingInstances'][0]['CurrentState']['Name']

    def terminate(self):
        try:
            res = self.conn.terminate_instances(InstanceIds = [self.id])
            if self.filename and os.path.exists(self.filename):
                os.remove(self.filename)
            return res['TerminatingInstances'][0]['CurrentState']['Name']
        except botocore.exceptions.ClientError as error:
            print(error)
            if self.filename and os.path.exists(self.filename):
                os.remove(self.filename)
            return None
