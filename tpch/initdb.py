import time
import logging
import os.path
from datetime import datetime

from . import utils
from .load import Load
from .helpers import Schema

CARDINALITIES = './schema/cardinalities.sql'


class InitDB(Schema):
    def __init__(self, conf, dsn, schema, logger, track):
        super().__init__(conf, dsn, schema, logger, track)

        # initdb is hardcoded and better be present in the INI file
        self.load = Load(self.conf.jobs['initdb'],
                         self.dsn,
                         self.schema,
                         self.logger,
                         self.track)

        self.steps = self.load.steps
        self.cpu = self.load.cpu

    def run(self, system, debug=False):
        "Initialize target database for TPC-H."
        self.system = system
        self.log("initializing the TPC-H schema")

        start = time.monotonic()

        for schema, name in [(self.schema.drop, "drop tables"),
                             (self.schema.tables, "create tables")]:
            self.install_schema(name, schema)

        # don't track installing the cardinalities view...
        self.install_schema("cardinalities", CARDINALITIES, tracking=False)

        # self.load.run() is verbose already
        # It loads the data and does the VACUUM ANALYZE on each table
        self.load.run(system, 'initdb')

        for sqlfile in self.schema.constraints:
            self.install_schema(sqlfile, sqlfile)

        end = time.monotonic()
        secs = end - start

        self.log("imported %d initial steps in %gs, using %d CPU",
                 len(self.steps), secs, self.cpu)
        return
