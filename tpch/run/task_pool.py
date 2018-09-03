import time
import logging
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED


class TaskPool():

    def __init__(self, cpu, duration, pause=1):
        self.cpu = cpu
        self.duration = duration
        self.pause = pause

        self.tasks_done = []
        self.previous_report_time = 0

    def report_progress(self):
        pass

    def handle_results(self, results):
        pass

    def run(self, fun, *args):
        """Run FUN with KWARGS as many times as possible for DURATION seconds,
        using as much as CPU cores in parallel. Return a list of results
        and the time we actually took in seconds.

        """
        self.pool = ProcessPoolExecutor(self.cpu)
        futures = []

        self.start = time.monotonic()

        # start CPU query streams in parallel
        for x in range(self.cpu):
            futures.append(self.pool.submit(fun, *args))

        while (time.monotonic() - self.start) < (self.duration):
            # we used to avoid busy looping too hard on the system when
            # running long queries (by TPC-H design), by adding a call to
            # time.sleep(self.pause) here.
            #
            # avoiding the sleep makes the TPCH driver use 100% of a CPU on
            # the loader machine, but because we mostly ever wait for query
            # results it seems fair to use that much power in exchange for
            # better results: we actually launch the next query as soon as
            # we are ready to do so.

            # collect results from the future as they are available,
            # and start other threads to keep them CPU busy
            done, not_done = wait(futures, return_when=FIRST_COMPLETED)

            ready = done - set(self.tasks_done)

            # grab results of done futures we didn't collect before
            for future in ready:
                self.tasks_done.append(future)
                self.handle_results(future.result())

            # it could be that while waiting for the futures to be ready we
            # went past assigned duration already, in that case don't start
            # new tasks
            #
            # otherwise and submit another stream of queries
            if (time.monotonic() - self.start) < (self.duration):
                for x in range(len(ready)):
                    futures.append(self.pool.submit(fun, *args))

            # now that the futures are queued to start, report our progress,
            # including track/register timings in a local database
            self.report_progress()

        # now we're timed out, so retrieve all remaining results
        done, not_done = wait(futures)
        ready = done - set(self.tasks_done)
        for future in ready:
            self.tasks_done.append(future)
            self.handle_results(future.result())

        self.pool.shutdown(wait=False)
        self.end = time.monotonic()

        return self.end - self.start
