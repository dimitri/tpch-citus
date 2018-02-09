SCHEMA        = 'make SCHEMA=%s -f Makefile.loader schema'
VACUUM        = 'make -f Makefile.loader vacuum'
CARDINALITIES = './schema/cardinalities.sql'

import time
from . import utils, pooling
from .load import Load

def initdb(step, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (scale_factor, children, step))
    return


class InitDB():
    def __init__(self, conf, kind = 'pgsql', phase = 'initdb'):
        self.conf = conf
        self.load = Load(conf)
        self.kind = kind

        if kind == 'pgsql':
            self.schema = self.conf.schema.pgsql
        elif kind == 'citus':
            self.schema = self.conf.schema.citus
        else:
            # that way, a filename might be given...
            # might be helpful, but it's not documented
            self.schema = kind

        self.phase = phase
        self.steps = self.conf.load[self.phase]

    def run(self, name, debug=False):
        "Initialize target database for TPC-H."
        print("%s: initializing the TPC-H schema" % (name))

        start = time.monotonic()

        # create the schema, load the 'initdb' phase of data
        # then install the extra constraints, and finally VACUUM ANALYZE
        print("%s: create initial schema, %s variant" % (name, self.kind))

        out = utils.run_command(SCHEMA % (self.schema))
        if debug:
            print(out)

        # install the cardinalities view
        out = utils.run_command(SCHEMA % (CARDINALITIES))
        if debug:
            print(out)

        # self.load.run() is verbose already
        self.load.run(name, self.phase)

        for sqlfile in self.conf.schema.constraints:
            print("%s: install constraints from '%s'" % (name, sqlfile))
            out = utils.run_command(SCHEMA % (sqlfile))

            if debug:
                print(out)

        print("%s: vacuum analyze" % (name))
        out = utils.run_command(VACUUM)
        if debug:
            print(out)

        end  = time.monotonic()
        secs = end - start

        print("%s: imported %d initial steps in %gs, using %d CPU" %
              (name, len(self.steps), secs, self.conf.scale.cpu))
        return

