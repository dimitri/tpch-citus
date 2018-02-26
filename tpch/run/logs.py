import sys
import logging
from multiprocessing import Process, Queue


def formatter():
    return logging.Formatter('%(asctime)s %(levelname)s %(message)s')


def logger(log_level):
    logger = logging.getLogger('TPCH')
    logger.setLevel(log_level)

    return logger


def setup_file_logger(logger, filename, log_level):
    fh = logging.FileHandler(filename, 'w')
    fh.setLevel(log_level)
    fh.setFormatter(formatter())
    logger.addHandler(fh)

    return


def setup_stdout_logger(logger, log_level):
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)
    ch.setFormatter(formatter())
    logger.addHandler(ch)

    return


def create_queue():
    queue = Queue(-1)
    return queue


def start_listener(logger, queue):
    listener = Process(
        name="log listener",
        target=consume_logs_from_queue,
        args=(queue,))

    listener.start()
    return listener


def consume_logs_from_queue(queue):
    while True:
        record = queue.get()
        if record is None:  # end has been signaled
            break

        # Adding code to actually do something with the message only
        # duplicates it in the logs/output. I don't know why. Not doing
        # anything with the record here seems to work, tho.
        #
        # logger = logging.getLogger(record.name)
        # logger.handle(record)
    return


def get_worker_logger(queue, log_level=logging.INFO):
    logger = logging.getLogger('TPCH')

    qh = logging.handlers.QueueHandler(queue)
    qh.setLevel(log_level)
    qh.setFormatter(formatter())
    logger.addHandler(qh)

    return logger
