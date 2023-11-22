import logging, sys
import logging.handlers


class OLSLogger:
    def __init__(self, module_name):
        # logging.basicConfig(
        #    stream=sys.stdout,
        #    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        #    level=logging.INFO,
        # )
        # self.logger = logging.getLogger(module_name)

        self.logger = logging.getLogger(module_name)
        # self.stdout_logger = logging.getLogger(module_name)

        # TODO: make loglevel configurable
        self.logger.setLevel(logging.INFO)
        # self.stdout_logger.setLevel(logging.INFO)

        # standardize log format
        formatter = logging.Formatter(
            "%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s: %(message)s"
        )

        # log to files
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/ols.log", maxBytes=(1048576 * 100), backupCount=7
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # also log to stdout

        stdoutHandler = logging.StreamHandler(sys.stdout)
        stdoutHandler.setFormatter(formatter)
        self.logger.addHandler(stdoutHandler)
