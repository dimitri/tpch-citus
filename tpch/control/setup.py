import os.path
import configparser
from collections import namedtuple

Run = namedtuple('Run', 'schedule systems')


class Setup():
    def __init__(self, filename):
        "Read our configuration file"
        self.filename = filename
        self.read()

    def create(self, schedule, systems):
        self.conf = configparser.ConfigParser()
        self.conf['run'] = {'schedule': schedule,
                            'systems': ", ".join(systems)}

        with open(self.filename, 'w') as configfile:
            self.conf.write(configfile)

        self.read()
        return

    def read(self):
        if os.path.exists(self.filename):
            self.conf = configparser.ConfigParser()
            self.conf.read(self.filename)
            self.run = Run(
                schedule = self.conf.get('run', 'schedule'),
                systems  = self.conf.get('run', 'systems').split(', ')
            )
        else:
            self.run = None
        return
