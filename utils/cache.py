import os
import pickle
import datetime as dt

from utils import ui, logger


_logger = logger.get_logger()


CACHE_BASEPATH = './cache'
CACHE_SUFFIX = 'pickle'


def exists(name: str, type: str) -> bool:
    exist = False

    filename = build_filename(name, type)
    if filename and os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                exist = True
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle exists: {str(e)}')

    return exist


def load(name: str, type: str) -> object:
    object = None

    filename = build_filename(name, type)
    if filename and os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                object = pickle.load(f)
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle load: {str(e)}')

    return object


def dump(object: object, name: str, type: str) -> bool:
    success = False

    filename = build_filename(name, type)
    if filename:
        try:
            with open(filename, 'wb') as f:
                pickle.dump(object, f, protocol=pickle.HIGHEST_PROTOCOL)  # TODO Why does dump() send LF's to console
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle dump: {str(e)}')
        else:
            success = True

    return success


def roll(type: str) -> tuple[bool, str]:
    success = True
    message = ''
    rolled = 0

    paths = get_filenames(type)
    for result_old in paths:
        file_old = f'{CACHE_BASEPATH}/{result_old}.{CACHE_SUFFIX}'
        date_time = dt.datetime.now().strftime(ui.DATE_FORMAT)
        result_new = f'{date_time}{result_old[10:]}'
        if result_new > result_old:
            file_new = f'{CACHE_BASEPATH}/{result_new}.{CACHE_SUFFIX}'
            try:
                os.replace(file_old, file_new)
            except OSError as e:
                success = False
                message = f'File error for {e.filename}: {e.strerror}'
                break
            else:
                rolled += 1

    if success:
        message = f'Rolled {rolled} file(s)'
        _logger.info(f'{__name__}: {message}')
    else:
        _logger.error(f'{__name__}: {message}')

    return success, message


def delete(type: str) -> tuple[bool, str]:
    success = True
    message = ''

    files = get_filenames(type)
    if files:
        paths = []
        date = dt.datetime.now().strftime(ui.DATE_FORMAT)
        for path in files:
            head, sep, tail = path.partition('.')
            parts = head.split('_')
            file_date = f'{parts[0]}'
            if file_date != date:
                file = f'{CACHE_BASEPATH}/{path}.{CACHE_SUFFIX}'
                paths += [file]

        if paths:
            deleted = 0
            for path in paths:
                try:
                    os.remove(path)
                except OSError as e:
                    success = False
                    message = f'File error for {e.filename}: {e.strerror}'
                    break
                else:
                    deleted += 1

            if success and deleted > 0:
                message = f'Deleted {deleted} file(s)'
        else:
            message = 'All files up to date'
    else:
        message = 'No files to delete'

    if success:
        _logger.info(f'{__name__}: {message}')
    else:
        _logger.error(f'{__name__}: {message}')

    return success, message


def get_filenames(type: str) -> list[str]:
    files = []
    with os.scandir(CACHE_BASEPATH) as entries:
        for item in entries:
            if item.is_file():
                head, sep, tail = item.name.partition('.')
                parts = head.split('_')
                if tail != CACHE_SUFFIX:
                    pass # Wrong file type
                elif len(parts) != 4:
                    pass # Bad filename structure
                elif parts[3] == type:
                    files += [head]

    files.sort()

    return files


def build_filename(name: str, type: str) -> str:
    filename = ''

    if name:
        date_time = dt.datetime.now().strftime(ui.DATE_FORMAT)
        filename = f'{CACHE_BASEPATH}/{date_time}_{name.lower()}_{type}.{CACHE_SUFFIX}'

    return filename
