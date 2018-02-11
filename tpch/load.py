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
        logging.info('%s: loaded step %d', self.name, arg)


class Load(DistributedTasks):
    def __init__(self, conf, phase):
        self.conf = conf
        self.phases = self.conf.load
        self.steps = self.phases[phase]

        self.dist = DistributedLoad(self.conf.scale.cpu)

    def report_progress(self, arg):
        logging.info('%s: loading step %s', self.name, arg)

    def run(self, name):
        "Load the next STEPs using as many as CPU cores."
        cpu = self.conf.scale.cpu

        logging.info("%s: loading %d steps of data using %d CPU: %s",
                     name, len(self.steps), cpu, self.steps)

        start = time.monotonic()

        res, secs = self.dist.run(
            name,
            load,
            self.steps,
            self.conf.scale.factor,
            self.conf.scale.children
        )

        logging.info("%s: vacuum analyze", name)
        out = utils.run_command(VACUUM)

        secs = time.monotonic() - start

        logging.info("%s: loaded %d steps of data in %gs, using %d CPU",
                     name, len(self.steps), secs, cpu)
        return
