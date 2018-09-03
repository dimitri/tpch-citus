import time
import logging
import os.path
from datetime import datetime

from . import utils
from .task_dist import DistributedTasks
from .helpers import Schema

MAKEFILE = os.path.join(os.path.dirname(__file__),
                        '..',
                        '..',
                        'Makefile.loader')

LOAD     = 'make -f %s DSN=%s SF=%s C=%s S=%s load'
VACUUM   = 'make -f %s DSN=%s vacuum'


def load(step, dsn, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    command = LOAD % (MAKEFILE, dsn, scale_factor, children, step)
    out, err = utils.run_command(command)

    if err:
        logger = logging.getLogger('TPCH')
        logger.error(command)
        for line in out:
            logger.error(line)
        for line in err:
            logger.error(line)

        raise RuntimeError("Failed to load step %s" % step)

    return


class DistributedLoad(DistributedTasks):
    def report_progress(self, arg):
        self.logger.info('%s: loaded step %d/%d for Scale Factor %d',
                         self.system,
                         arg,
                         self.children,
                         self.scale_factor)


class Load(Schema):
    def __init__(self, conf, dsn, schema, logger, track):
        super().__init__(conf, dsn, schema, logger, track)

        # conf is expected to be a Load namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.steps = self.conf.steps
        self.cpu = self.conf.cpu

        self.dist = DistributedLoad(self.cpu)
        self.dist.scale_factor = self.conf.scale_factor
        self.dist.children = self.conf.children
        self.dist.track = self.track
        self.dist.logger = self.logger

    def run(self, system, phase):
        "Load the next STEPs using as many as CPU cores."
        self.system = system
        self.dist.system = system

        self.log("loading %d steps of data using %d CPU: %s",
                 len(self.steps), self.cpu, self.steps)

        start = datetime.now()

        res, secs = self.dist.run(
            load,
            self.steps,
            self.dsn,
            self.conf.scale_factor,
            self.conf.children
        )
        self.track.register_job(
            phase, start=start, secs=secs, steps=self.steps)

        self.log("vacuum analyze")
        for sqlfile in self.schema.vacuum:
            self.install_schema(sqlfile, sqlfile, silent=True)

        self.log("loaded %d steps of data in %gs, using %d CPU",
                 len(self.steps), secs, self.cpu)
        return
