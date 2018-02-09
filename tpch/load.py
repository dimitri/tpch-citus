LOAD   = 'make -f Makefile.loader SF=%s C=%s S=%s load'

from . import utils, pooling


def load(step, scale_factor, children):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (scale_factor, children, step))
    return


class Load():
    def __init__(self, conf):
        self.conf = conf
        self.phases = self.conf.load

    def run(self, name, phase):
        "Load the next STEPs using as many as CPU cores."
        cpu = self.conf.scale.cpu
        steps = self.phases[phase]

        print("%s: loading %d steps of data using %d CPU: %s" % (
            name, len(steps), cpu, steps))

        res, secs = pooling.execute_on_one_core_per_arglist(
            name, cpu, load,
            steps,
            self.conf.scale.factor,
            self.conf.scale.children
        )

        print("%s: loaded %d steps of data in %gs, using %d CPU" %
              (name, len(steps), secs, cpu))
        return

