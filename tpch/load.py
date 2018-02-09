LOAD   = 'make -f Makefile.loader SF=%s C=%s S=%s load'
VACUUM = 'make -f Makefile.loader vacuum'

import time
from . import utils, pooling


def load(step, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (scale_factor, children, step))
    return


class Load():
    def __init__(self, conf, phase):
        self.conf = conf
        self.phases = self.conf.load
        self.steps = self.phases[phase]

    def run(self, name):
        "Load the next STEPs using as many as CPU cores."
        cpu = self.conf.scale.cpu

        print("%s: loading %d steps of data using %d CPU: %s" % (
            name, len(self.steps), cpu, self.steps))

        start = time.monotonic()

        res, secs = pooling.execute_on_one_core_per_arglist(
            name,
            cpu,
            load,
            self.steps,
            self.conf.scale.factor,
            self.conf.scale.children
        )

        print("%s: vacuum analyze" % (name))
        out = utils.run_command(VACUUM)

        secs = time.monotonic() - start

        print("%s: loaded %d steps of data in %gs, using %d CPU" %
              (name, len(self.steps), secs, cpu))
        return

