import time
import logging
from . import utils
from .load import Load

SCHEMA        = 'make SCHEMA=%s -f Makefile.loader schema'
CARDINALITIES = './schema/cardinalities.sql'


def initdb(step, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (scale_factor, children, step))
    return


class InitDB():
    def __init__(self, conf, kind='pgsql', phase='initdb'):
        self.conf = conf
        self.load = Load(conf, phase)
        self.kind = kind

        if kind == 'pgsql':
            self.tables = self.conf.pgsql.tables
            self.constraints = self.conf.pgsql.constraints
        elif kind == 'citus':
            self.tables = self.conf.citus.tables
            self.constraints = self.conf.citus.constraints
        else:
            raise ValueError

        self.phase = phase
        self.steps = self.conf.load[self.phase]

    def run(self, name, debug=False):
        "Initialize target database for TPC-H."
        print("%s: initializing the TPC-H schema" % (name))

        start = time.monotonic()

        # create the schema, load the 'initdb' phase of data
        # then install the extra constraints, and finally VACUUM ANALYZE
        logging.info("%s: create initial schema, %s variant", name, self.kind)

        out = utils.run_command(SCHEMA % (self.tables))
        for line in out:
            logging.debug(line)

        # install the cardinalities view
        out = utils.run_command(SCHEMA % (CARDINALITIES))
        for line in out:
            logging.debug(line)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(name)

        for sqlfile in self.constraints:
            logging.info("%s: install constraints from '%s'", name, sqlfile)
            out = utils.run_command(SCHEMA % (sqlfile))

            for line in out:
                logging.debug(line)

        end = time.monotonic()
        secs = end - start

        logging.info("%s: imported %d initial steps in %gs, using %d CPU",
                     name, len(self.steps), secs, self.conf.scale.cpu)
        return
