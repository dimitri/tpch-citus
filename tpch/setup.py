import configparser
from collections import namedtuple

from . import utils

Scale   = namedtuple('Scale', 'cpu factor children')
Stream  = namedtuple('Stream', 'queries duration')
Schema  = namedtuple('Schema', 'tables constraints')
Results = namedtuple('Results', 'dsn')


class Setup():
    def __init__(self, filename):
        "Read our configuration file"
        conf = configparser.ConfigParser()
        conf.read(filename)

        self.scale = Scale(
            cpu = conf.getint('scale', 'cpu'),
            factor = conf.getint('scale', 'factor'),
            children = conf.getint('scale', 'children'))

        self.load = {}
        for option in conf.options('load'):
            step_range = conf.get('load', option)
            self.load[option] = utils.expand_step_range(step_range)

        self.stream = Stream(
            queries = conf.get('stream', 'queries'),
            duration = conf.getint('stream', 'duration'))

        self.pgsql = Schema(
            tables = conf.get('pgsql', 'tables'),
            constraints = conf.get('pgsql', 'constraints').split(' '))

        self.citus = Schema(
            tables = conf.get('citus', 'tables'),
            constraints = conf.get('citus', 'constraints').split(' '))

        self.results = Results(dsn = conf.get('results', 'dsn'))

    def __repr__(self):
        return "%s\n  %s\n  %s\n  %s\n  %s\n  %s" % (
            object.__repr__(self),
            self.scale, self.load, self.stream, self.schema, self.results)
