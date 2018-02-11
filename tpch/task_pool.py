import time
import logging
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED


class TaskPool():

    def __init__(self, cpu, duration, pause=1):
        self.cpu = cpu
        self.duration = duration
        self.pause = pause

        self.tasks_done = []

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
            time.sleep(self.pause)
            # collect results from the future as they are available,
            # and start other threads to keep them CPU busy
            done, not_done = wait(futures, return_when=FIRST_COMPLETED)

            ready = done - set(self.tasks_done)

            # grab results of done futures we didn't collect before
            for future in ready:
                self.tasks_done.append(future)
                self.handle_results(future.result())

            for x in range(len(ready)):
                # and submit another stream of queries
                futures.append(self.pool.submit(fun, *args))

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
