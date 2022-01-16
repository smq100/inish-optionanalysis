import logging
from logging import Logger


LOG_DIR = './log'


def get_logger(level: int = None, logfile: str = '') -> Logger:
    logger = logging.getLogger('analysis')

    if level is None:
        logger.info(f'{__name__}: Returning existing logger')
    else:
        logger.handlers = []
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Prevent logging from propagating to the root logger

        # Console handler
        cformat = logging.Formatter('%(levelname)s: %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(cformat)
        ch.setLevel(level)
        logger.addHandler(ch)

        # File handler
        if logfile:
            fformat = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
            fh = logging.FileHandler(f'{LOG_DIR}/{logfile}.log', 'w+')
            fh.setFormatter(fformat)
            fh.setLevel(logging.DEBUG)
            logger.addHandler(fh)

        logger.info(f'{__name__}: Created new logger')

    return logger
