import logging, sys
import logging.handlers

class OLSLogger:
    def __init__(self, module_name):
        #logging.basicConfig(
        #    stream=sys.stdout,
        #    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        #    level=logging.INFO,
        #)
        #self.logger = logging.getLogger(module_name)

        self.logger = logging.getLogger(module_name)
        #self.stdout_logger = logging.getLogger(module_name)

        # TODO: make loglevel configurable
        self.logger.setLevel(logging.INFO)
        #self.stdout_logger.setLevel(logging.INFO)

        # standardize log format
        formatter = logging.Formatter("%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s: %(message)s")

        # also log to stdout

        stdoutHandler=logging.StreamHandler(sys.stdout)
        stdoutHandler.setFormatter(formatter)
        self.logger.addHandler(stdoutHandler)

