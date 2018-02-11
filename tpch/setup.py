import re
import json
import configparser
from collections import namedtuple

from . import utils

Scale   = namedtuple('Scale', 'cpu factor children')
Stream  = namedtuple('Stream', 'queries duration cpu')
Load    = namedtuple('Load', 'scale_factor children steps cpu')
Schema  = namedtuple('Schema', 'tables constraints drop')
Results = namedtuple('Results', 'dsn')


class Setup():
    def __init__(self, filename):
        "Read our configuration file"
        self.conf = configparser.ConfigParser()
        self.conf.read(filename)

        self.jobs = {}
        self.schedules = {}

        for option in self.conf.options('schedule'):
            s = self.conf.get('schedule', option)
            self.schedules[option] = self.parse_run_job(s)

        self.scale = Scale(
            cpu = self.conf.getint('scale', 'cpu'),
            factor = self.conf.getint('scale', 'factor'),
            children = self.conf.getint('scale', 'children'))


        for section in self.conf.sections():
            if self.conf.has_option(section, 'type'):
                if self.conf.get(section, 'type') == 'load':
                    step_range = self.conf.get(section, 'steps')
                    steps = utils.expand_step_range(step_range)

                    if self.conf.has_option(section, 'cpu'):
                        cpu = self.conf.getint(section, 'cpu')
                    else:
                        cpu = self.scale.cpu

                    job = Load(
                        scale_factor = self.scale.factor,
                        children     = self.scale.children,
                        steps        = steps,
                        cpu          = cpu
                    )
                    self.jobs[section] = job

                elif self.conf.get(section, 'type') == 'stream':
                    queries = self.conf.get(section, 'queries')
                    duration = self.conf.getint(section, 'duration')

                    if self.conf.has_option(section, 'cpu'):
                        cpu = self.conf.getint(section, 'cpu')
                    else:
                        cpu = self.scale.cpu

                    job = Stream(queries=queries, duration=duration, cpu=cpu)
                    self.jobs[section] = job

        self.pgsql = Schema(
            tables = self.conf.get('pgsql', 'tables'),
            constraints = self.conf.get('pgsql', 'constraints').split(' '),
            drop = self.conf.get('pgsql', 'drop'))

        self.citus = Schema(
            tables = self.conf.get('citus', 'tables'),
            constraints = self.conf.get('citus', 'constraints').split(' '),
            drop = self.conf.get('pgsql', 'drop'))

        self.results = Results(dsn = self.conf.get('results', 'dsn'))


    def parse_schedule(self, spec):
        "Parse a test schedule: a series of comma-separated job names"
        joblist = [x.strip() for x in spec.split(',') if x]

        for job in joblist:
            if job not in self.conf.options('run'):
                raise ValueError("%s: unknown job in the run section" % job)

        return joblist


    def parse_run_job(self, jobspec):
        "Parse a TPCH RUN job specification into something we can run"
        speclist = [x.strip() for x in jobspec.split(',') if x]

        jobs = []
        for spec in speclist:
            if 'and' in spec:
                p = re.compile('\s*and\s*')
                jobs.append(p.split(spec))
            else:
                jobs.append(spec)

        return jobs


    def to_json(self):
        config = {}
        for section in self.conf:
            config[section] = {}
            for option, value in self.conf.items(section):
                value = value.strip()

                if ',' in value:
                    value = [x.strip() for x in value.split(',') if x]
                elif ' ' in value.strip():
                    value = [x.strip() for x in value.split() if x]
                else:
                    try:
                        value = int(value)
                    except:
                        pass

                config[section][option] = value

        return json.dumps(config, indent=1)

