#
# System commands to run to make things happen
#
# We use a Makefile to make it easier to hack around the scripts and change
# or improve the commands.
#
LOAD   = 'make -f Makefile.loader SF=%s C=%s S=%s load'
STREAM = "make -f Makefile.loader STREAM='%s' stream"

from . import utils


def load(step):
    # the LOAD phase doesn't bring any particulary useful information on the
    # table, so just forget about any output here, really.
    utils.run_command(LOAD % (step))
    return

