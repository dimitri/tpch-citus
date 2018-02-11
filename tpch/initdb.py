import time
import logging
from datetime import datetime
from . import utils
from .load import Load

SCHEMA        = 'make SCHEMA=%s -f Makefile.loader schema'
CARDINALITIES = './schema/cardinalities.sql'

def run_schema_file(filename, results=None, name=None):
    now = datetime.now()
    start = time.monotonic()

    out = utils.run_command(SCHEMA % (filename))
    for line in out:
        logging.debug(line)

    secs =  time.monotonic() - start

    if results and name:
        results.register_initdb_step(name, now, secs)

    return

class InitDB():
    def __init__(self, conf, results, kind='pgsql'):
        self.conf = conf
        self.kind = kind

        self.results = results

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
        self.load = Load(self.conf.jobs['initdb'], self.results)
        self.steps = self.load.steps
        self.cpu = self.load.cpu

    def run(self, system, debug=False):
        "Initialize target database for TPC-H."
        logging.info("%s: initializing the TPC-H schema" % (system))

        start = time.monotonic()

        # create the schema, load the 'initdb' phase of data
        # then install the extra constraints, and finally VACUUM ANALYZE
        logging.info("%s: create initial schema, %s variant", system, self.kind)

        run_schema_file(self.drop, results=self.results, name="drop tables")
        run_schema_file(self.tables, results=self.results, name="create tables")
        run_schema_file(CARDINALITIES)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(system, 'initdb')

        for sqlfile in self.constraints:
            logging.info("%s: install constraints from '%s'", system, sqlfile)
            run_schema_file(sqlfile, results=self.results, name=sqlfile)

        end = time.monotonic()
        secs = end - start

        logging.info("%s: imported %d initial steps in %gs, using %d CPU",
                     system, len(self.steps), secs, self.cpu)
        return
