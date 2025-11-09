import os
import logging
import traceback
from random import randint


def generate_correlation_id():
    """
    A random correlation id
    """
    random_numbers = [str(randint(100, 999)) for i in range(4)]
    correlation_id = "_".join(random_numbers)
    return correlation_id

class RequestLogger:
    def __init__(self, correlator: str = None):
        self.logger = logging.getLogger("tmonitor_logger")
        handler = logging.StreamHandler()
        handler.Formatter="[%(filename)20s - %(funcName)25s - Line: %(lineno)4s] %(correlator)s %(levelname)s - %(message)s"
        self.logger.setLevel(os.getenv("TMONITOR_LOG_LEVEL", "INFO"))
        self.logger.addHandler(handler)
        if correlator:
            self.correlator = correlator
        else:
            self.correlator = generate_correlation_id()

    def debug(self, message):
        self.logger.debug(message, extra={"correlator": self.correlator})

    def info(self, message):
        self.logger.info(message, extra={"correlator": self.correlator})

    def exception(self, message):
        trace_str = traceback.format_exc().replace("\n", "\\n")
        self.logger.error(f"{message}: {trace_str}", extra={"correlator": self.correlator})

    def critical(self, message):
        self.logger.critical(message, extra={"correlator": self.correlator})


if __name__=="__main__":
    r = RequestLogger()

    r.debug("some debugging messge")
    r.info("an info message")
    r.critical("A critical error")
