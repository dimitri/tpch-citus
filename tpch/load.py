import time
import logging
import os.path
from datetime import datetime

from . import utils
from .task_dist import DistributedTasks

MAKEFILE = os.path.join(os.path.dirname(__file__), '..', 'Makefile.loader')
LOAD     = 'make -f %s DSN=%s SF=%s C=%s S=%s load'
VACUUM   = 'make -f %s DSN=%s vacuum'


def load(step, dsn, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (MAKEFILE, dsn, scale_factor, children, step))
    return


class DistributedLoad(DistributedTasks):
    def report_progress(self, arg):
        self.logger.info('%s: loaded step %d/%d for Scale Factor %d',
                         self.system,
                         arg,
                         self.children,
                         self.scale_factor)


class Load():
    def __init__(self, conf, dsn, schema, logger, track):
        # conf is expected to be a Load namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.dsn = dsn
        self.conf = conf
        self.steps = self.conf.steps
        self.cpu = self.conf.cpu
        self.schema = schema

        self.track = track
        self.logger = logger

        self.dist = DistributedLoad(self.cpu)
        self.dist.scale_factor = self.conf.scale_factor
        self.dist.children = self.conf.children
        self.dist.track = self.track
        self.dist.logger = self.logger

    def run(self, system, phase):
        "Load the next STEPs using as many as CPU cores."
        self.system = system
        self.dist.system = system

        self.logger.info("%s: loading %d steps of data using %d CPU: %s",
                         system, len(self.steps), self.cpu, self.steps)

        start = datetime.now()

        res, secs = self.dist.run(
            load,
            self.steps,
            self.dsn,
            self.conf.scale_factor,
            self.conf.children
        )
        self.track.register_job(phase, start=start, secs=secs, steps=self.steps)

        self.logger.info("%s: vacuum analyze", self.system)
        vstart, vsecs = utils.run_schema_file(self.dsn, self.schema.vacuum)
        self.track.register_job("vacuum analyze", start=vstart, secs=vsecs)

        self.logger.info("%s: loaded %d steps of data in %gs, using %d CPU",
                         system,
                         len(self.steps),
                         secs,
                         self.cpu)
        return
