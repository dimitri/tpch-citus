import time
import logging

from . import utils
from .task_dist import DistributedTasks

LOAD   = 'make -f Makefile.loader SF=%s C=%s S=%s load'
VACUUM = 'make -f Makefile.loader vacuum'


def load(step, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (scale_factor, children, step))
    return


class DistributedLoad(DistributedTasks):
    def report_progress(self, arg):
        logging.info('%s: loaded step %d/%d for Scale Factor %d',
                     self.name,
                     arg,
                     self.children,
                     self.scale_factor
        )


class Load(DistributedTasks):
    def __init__(self, conf):
        # conf is expected to be a Load namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.conf = conf
        self.steps = self.conf.steps
        self.cpu = self.conf.cpu

        self.dist = DistributedLoad(self.cpu)
        self.dist.scale_factor = self.conf.scale_factor
        self.dist.children = self.conf.children

    def report_progress(self, arg):
        logging.info('%s: loading step %s', self.name, arg)

    def run(self, name):
        "Load the next STEPs using as many as CPU cores."
        logging.info("%s: loading %d steps of data using %d CPU: %s",
                     name, len(self.steps), self.cpu, self.steps)

        start = time.monotonic()

        res, secs = self.dist.run(
            name,
            load,
            self.steps,
            self.conf.scale_factor,
            self.conf.children
        )

        logging.info("%s: vacuum analyze", name)
        out = utils.run_command(VACUUM)

        secs = time.monotonic() - start

        logging.info("%s: loaded %d steps of data in %gs, using %d CPU",
                     name, len(self.steps), secs, self.cpu)
        return
