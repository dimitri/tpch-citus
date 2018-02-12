import time
import logging
from datetime import datetime

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
                     self.system,
                     arg,
                     self.children,
                     self.scale_factor
        )

class Load():
    def __init__(self, conf, track):
        # conf is expected to be a Load namedtuple, see setup.py
        # extra code so that we can "walk like a duck" if needed
        self.conf = conf
        self.steps = self.conf.steps
        self.cpu = self.conf.cpu

        self.track = track

        self.dist = DistributedLoad(self.cpu)
        self.dist.scale_factor = self.conf.scale_factor
        self.dist.children = self.conf.children
        self.dist.track = self.track

    def run(self, system, phase):
        "Load the next STEPs using as many as CPU cores."
        self.system = system
        self.dist.system = system

        logging.info("%s: loading %d steps of data using %d CPU: %s",
                     system, len(self.steps), self.cpu, self.steps)

        start = datetime.now()

        res, secs = self.dist.run(
            load,
            self.steps,
            self.conf.scale_factor,
            self.conf.children
        )
        vsecs = self.vacuum()

        self.track.register_job(phase, start=start,
                                secs=secs, vsecs=vsecs, steps=self.steps)

        logging.info("%s: loaded %d steps of data in %gs, using %d CPU",
                     system, len(self.steps), secs, self.cpu)
        return

    def vacuum(self):
        start = time.monotonic()

        logging.info("%s: vacuum analyze", self.system)
        out = utils.run_command(VACUUM)

        for line in out:
            logging.debug(line)

        return time.monotonic() - start
