import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

if os.getenv("EXTERNAL_TEST") == "true":
    LOG_DIR = os.path.join(os.environ["WORKSPACE"], ".results/test_execution_logs")
else:
    LOG_DIR = os.path.join(
        os.environ["WORKSPACE"], ".teflo/.results/test_execution_logs"
    )
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)


class CSS_Logger(object):
    _logger = None

    def __new__(cls, *args, **kwargs):
        if cls._logger is None:
            cls._logger = super(CSS_Logger, cls).__new__(cls)
            # Put any initialization here.
            cls._logger = logging.getLogger(args[0])
            cls._logger.setLevel(logging.DEBUG)

            pytest_current_test = os.environ.get("PYTEST_CURRENT_TEST")
            split_test_name = pytest_current_test.split("::")[1]
            short_test_name = split_test_name.split(" ")[0]

            datestring = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            filename = "{}_{}.log".format(short_test_name, datestring)
            filepath = os.path.join(LOG_DIR, filename)

            # Create a file handler for logging level above DEBUG
            file_handler = RotatingFileHandler(
                filepath, maxBytes=1024 * 1024 * 1024, backupCount=20
            )

            # Create a logging format
            log_formatter = logging.Formatter(
                "%(asctime)s  "
                "[%(levelname)s]  "
                "%(module)s:%(lineno)d  "
                "%(message)s"
            )
            file_handler.setFormatter(log_formatter)

            # Create a stream handler for logging level above INFO
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(log_formatter)

            # Add the handlers to the logger
            cls._logger.addHandler(file_handler)
            cls._logger.addHandler(stream_handler)

        return cls._logger
