import configparser
from collections import namedtuple

Scale   = namedtuple('Scale', 'cpu factor children')
Stream  = namedtuple('Stream', 'queries duration')
Schema  = namedtuple('Schema', 'pgsql citus constraints')
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
            self.load[option] = conf.get('load', option)

        self.stream = Stream(
            queries = conf.get('stream', 'queries'),
            duration = conf.getint('stream', 'duration'))

        self.schema = Schema(
            pgsql = conf.get('schema', 'pgsql'),
            citus = conf.get('schema', 'citus'),
            constraints = conf.get('schema', 'constraints').split(' '))

        self.results = Results(dsn = conf.get('results', 'dsn'))

    def __repr__(self):
        return "%s\n  %s\n  %s\n  %s\n  %s\n  %s" % (
            object.__repr__(self),
            self.scale, self.load, self.stream, self.schema, self.results)
