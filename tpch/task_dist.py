import time
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed


class DistributedTasks():

    def __init__(self, cpu):
        self.cpu = cpu

    def report_progress(self, arg):
        pass

    def run(self, name, fun, arglist, *args):
        """Run FUN as many times as len(ARGLIST) and with an entry from ARGLIST
           each time, concurrently, on as many as CPU cores.

        FUN is called as if by: [fun(x, *args) for x in arglist].
        """
        self.name = name
        self.start = time.monotonic()

        pool = ProcessPoolExecutor(self.cpu)
        results = []

        fargs = {pool.submit(fun, arg, *args): arg for arg in arglist}

        for future in as_completed(fargs):
            arg = fargs[future]
            self.report_progress(arg)
            results.append(future.result())

        pool.shutdown(wait=False)
        self.end = time.monotonic()

        return results, self.end - self.start
