import time
import logging
import os.path
from datetime import datetime

from . import utils
from .load import Load

MAKEFILE      = os.path.join(os.path.dirname(__file__), '..', 'Makefile.loader')
SCHEMA        = 'make -f %s DSN=%s SCHEMA=%s schema'
CARDINALITIES = './schema/cardinalities.sql'


def run_schema_file(dsn, filename, track=None, name=None, debug=False):
    now = datetime.now()
    start = time.monotonic()

    out = utils.run_command(SCHEMA % (MAKEFILE, dsn, filename))

    if debug:
        for line in out:
            logger = logging.getLogger('TPCH')
            logger.debug(line)

    secs = time.monotonic() - start

    if track and name:
        track.register_job(name, start=now, secs=secs)

    return


class InitDB():
    def __init__(self, dsn, conf, logger, track, kind='pgsql'):
        self.dsn = dsn
        self.conf = conf
        self.kind = kind
        self.logger = logger

        self.track = track

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
        self.load = Load(self.conf.jobs['initdb'],
                         self.dsn,
                         self.logger,
                         self.track)
        self.steps = self.load.steps
        self.cpu = self.load.cpu

    def run(self, system, debug=False):
        "Initialize target database for TPC-H."
        self.logger.info("%s: initializing the TPC-H schema" % (system))

        start = time.monotonic()

        # create the schema, load the 'initdb' phase of data
        # then install the extra constraints, and finally VACUUM ANALYZE
        self.logger.info("%s: create initial schema, %s variant",
                         system, self.kind)

        run_schema_file(self.dsn, self.drop, self.track, "drop tables")
        run_schema_file(self.dsn, self.tables, self.track, "create tables")
        run_schema_file(self.dsn, CARDINALITIES)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(system, 'initdb')

        for sqlfile in self.constraints:
            self.logger.info("%s: install constraints from '%s'",
                             system, sqlfile)
            run_schema_file(self.dsn, sqlfile, self.track, sqlfile)

        end = time.monotonic()
        secs = end - start

        self.logger.info("%s: imported %d initial steps in %gs, using %d CPU",
                         system, len(self.steps), secs, self.cpu)
        return
