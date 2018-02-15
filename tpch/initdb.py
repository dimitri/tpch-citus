import time
import logging
import os.path
from datetime import datetime

from . import utils
from .load import Load

CARDINALITIES = './schema/cardinalities.sql'


class InitDB():
    def __init__(self, dsn, conf, schema, logger, track):
        self.dsn = dsn
        self.conf = conf
        self.schema = schema

        self.logger = logger
        self.track = track

        # initdb is hardcoded and better be present in the INI file
        # self.load is a Load namedtuple instance
        self.load = Load(self.conf.jobs['initdb'],
                         self.dsn,
                         self.schema,
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
        self.logger.info("%s: create initial schema", system)

        for schema, name in [(self.schema.drop, "drop tables"),
                             (self.schema.tables, "create tables")]:
            sstart, ssecs = utils.run_schema_file(self.dsn, schema, self.logger)
            self.track.register_job(name, start=sstart, secs=ssecs)

        # don't track installing the cardinalities view...
        utils.run_schema_file(self.dsn, CARDINALITIES, self.logger)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(system, 'initdb')

        self.logger.info("%s: install pkeys and fkeys", system)
        for sqlfile in self.schema.constraints:
            cstart, csecs = utils.run_schema_file(self.dsn,
                                                  sqlfile,
                                                  self.logger)
            self.track.register_job(sqlfile, start=cstart, secs=csecs)

        end = time.monotonic()
        secs = end - start

        self.logger.info("%s: imported %d initial steps in %gs, using %d CPU",
                         system, len(self.steps), secs, self.cpu)
        return
