import time
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

def execute_on_one_core_per_arglist(name, cpu, fun, arglist, *args,
                                    verbose=False):
    """Run FUN as many times as len(ARGLIST) and with an entry from ARGLIST each
       time, concurrently, on as many as CPU cores.

    FUN is called as if by: [fun(x, *args) for x in arglist].
    """
    pool = ProcessPoolExecutor(cpu)
    results = []
    futures = []
    i = 0

    start = time.monotonic()

    for arg in arglist:
        i = print_dots(i)
        futures.append(pool.submit(fun, arg, *args))

    i = print_dots(i, char = '§')
    done, not_done = wait(futures)

    for future in done:
        results.append(future.result())

    if verbose:
        print("¶")

    pool.shutdown(wait=False)
    end = time.monotonic()
    return results, end-start


def repeat_for_a_while_on_many_cores(name, cpu, duration, fun, *args,
                                     verbose=False):
    """Run FUN with KWARGS as many times as possible for DURATION seconds, using
    as much as CPU cores in parallel. Return a list of results and the time
    we actually took in seconds.

    """
    pool = ProcessPoolExecutor(cpu)
    futures   = []
    seen_done = []                # wait() keeps returning same done futures

    i = 0
    results = []
    start = time.monotonic()

    # start CPU query streams in parallel
    for x in range(cpu):
        futures.append(pool.submit(fun, *args))

    while (time.monotonic() - start) < (duration):
        time.sleep(1)
        # collect results from the future as they are available,
        # and start other threads to keep them CPU busy
        done, not_done = wait(futures, return_when=FIRST_COMPLETED)

        unseen_done = done - set(seen_done)
        nb = len(unseen_done)

        # grab results of done futures we didn't collect before
        for future in unseen_done:
            i = print_dots(i)
            seen_done.append(future)
            results.append(future.result())

        for x in range(nb):
            # and submit another stream of queries
            futures.append(pool.submit(fun, *args))

    # signal we're done with submitting new tasks, shutdown time
    i = print_dots(i, char = '§')

    # now we're timed out, so retrieve all remaining results
    done, not_done = wait(futures)
    unseen_done = done - set(seen_done)
    for future in unseen_done:
        i = print_dots(i)
        seen_done.append(future)
        results.append(future.result())

    # and we're done!
    if verbose:
        print("¶")
    pool.shutdown(wait=False)
    end = time.monotonic()

    return results, end-start

def print_dots(i, per_line = 60, char = '.', verbose = False):
    if verbose:
        i = i+1
        if i % 60 == 0:
            print(char)
        else:
            print(char, end="", flush=True)

        return i
