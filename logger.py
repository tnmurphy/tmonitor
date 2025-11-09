"""
A Module for logging API calls in a FastAPI app

Ensures that such calls all have a correlator so you
know which logs come from which request.

Copyright (c) 2025 Timothy Norman Murphy <tnmurphy@gmail.com>

See the LICENSE file in the current directory

"""

import logging
import traceback
from random import randint
import os
import sys

<<<<<<< HEAD

=======
>>>>>>> 878f49e (Fix the main install instructions in the README/)
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

        # zap the existing handlers so we don't get duplicate logs
        if self.logger.handlers:
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(filename)20s - %(funcName)25s - Line: %(lineno)4s] %(correlator)s %(levelname)s - %(message)s"
            )
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(os.getenv("TMONITOR_LOG_LEVEL", "INFO"))
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
        self.logger.error(
            f"{message}: {trace_str}", extra={"correlator": self.correlator}
        )

    def critical(self, message):
        self.logger.critical(message, extra={"correlator": self.correlator})


if __name__ == "__main__":
    r = RequestLogger()

    r.debug("some debugging messge")
    r.info("an info message")
    r.critical("A critical error")
