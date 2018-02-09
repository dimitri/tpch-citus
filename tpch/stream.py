STREAM = "make -f Makefile.loader STREAM='%s' stream"

from . import utils, pooling


def stream(queries):
    output = utils.run_command(STREAM % (queries))
    return utils.parse_psql_timings(queries)


class Stream():
    def __init__(self, conf):
        self.conf = conf
        self.queries = self.conf.stream.queries
        self.duration = self.conf.stream.duration


    def run(self, name):
        """Stream the given list of QUERIES on as many as CPU cores for given
        DURATION in minutes.

        """
        cpu = self.conf.scale.cpu

        print("Running TPCH on %s with %d CPUs for %ds, stream %s" %
              (name, cpu, self.duration, self.queries)
        )

        qtimings, secs = pooling.repeat_for_a_while_on_many_cores(
            name, cpu, self.duration, stream, self.queries
        )

        print("%s: executed %d streams of %d queries in %gs, using %d CPU" %
              (name, len(qtimings), len(qtimings[0]), secs, cpu)
        )
        return
