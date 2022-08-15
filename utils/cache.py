import os
import pickle
import datetime as dt

from utils import ui, logger


_logger = logger.get_logger()


CACHE_BASEPATH = './cache'
CACHE_SUFFIX = 'pickle'


def exists(name: str, type: str) -> bool:
    exist = False
    filename = get_filename(name, type)

    if filename and os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                exist = True
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle exists: {str(e)}')

    return exist


def load(name: str, type: str) -> object:
    object = None
    filename = get_filename(name, type)

    if filename and os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                object = pickle.load(f)
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle load: {str(e)}')

    return object


def dump(object: object, name: str, type: str) -> bool:
    success = False
    filename = get_filename(name, type)

    if filename:
        try:
            with open(filename, 'wb') as f:
                pickle.dump(object, f, protocol=pickle.HIGHEST_PROTOCOL)  # TODO Why does dump() send LF's to console
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle dump: {str(e)}')
        else:
            success = True

    return success


def get_filename(name: str, type: str) -> str:
    filename = ''

    if name:
        date_time = dt.datetime.now().strftime(ui.DATE_FORMAT)
        filename = f'{CACHE_BASEPATH}/{date_time}_{name.lower()}_{type}.{CACHE_SUFFIX}'

    return filename
