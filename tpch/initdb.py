import time
import logging
from . import utils
from .load import Load

SCHEMA        = 'make SCHEMA=%s -f Makefile.loader schema'
CARDINALITIES = './schema/cardinalities.sql'

def run_schema_file(filename):
    out = utils.run_command(SCHEMA % (filename))
    for line in out:
        logging.debug(line)


class InitDB():
    def __init__(self, conf, kind='pgsql'):
        self.conf = conf
        self.kind = kind

        if kind == 'pgsql':
            self.tables = self.conf.pgsql.tables
            self.constraints = self.conf.pgsql.constraints
            self.drop = self.conf.pgsql.drop
        elif kind == 'citus':
            self.tables = self.conf.citus.tables
            self.constraints = self.conf.citus.constraints
            self.drop = self.conf.citus.drop
        else:
            raise ValueError

        # initdb is hardcoded and better be present in the INI file
        # self.load is a Load namedtuple instance
        self.load = Load(self.conf.jobs['initdb'])
        self.steps = self.load.steps
        self.cpu = self.load.cpu

    def run(self, name, debug=False):
        "Initialize target database for TPC-H."
        logging.info("%s: initializing the TPC-H schema" % (name))

        start = time.monotonic()

        # create the schema, load the 'initdb' phase of data
        # then install the extra constraints, and finally VACUUM ANALYZE
        logging.info("%s: create initial schema, %s variant", name, self.kind)

        run_schema_file(self.drop)
        run_schema_file(self.tables)
        run_schema_file(CARDINALITIES)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(name)

        for sqlfile in self.constraints:
            logging.info("%s: install constraints from '%s'", name, sqlfile)
            run_schema_file(sqlfile)

        end = time.monotonic()
        secs = end - start

        logging.info("%s: imported %d initial steps in %gs, using %d CPU",
                     name, len(self.steps), secs, self.cpu)
        return
