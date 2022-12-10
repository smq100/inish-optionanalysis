from pathlib import Path
import pickle
import datetime as dt

from utils import ui, logger


_logger = logger.get_logger()


CACHE_BASEPATH = './cache'
CACHE_SUFFIX = 'pickle'
CACHE_TODAY_ONLY = False


def exists(name: str, type: str, today_only: bool = True) -> bool:
    if not name:
        raise AssertionError('Must include \'name\'')
    if not type:
        raise AssertionError('Must include \'type\'')

    name = name.lower()
    type = type.lower()
    filenames = []
    names = get_filenames(name, type)
    if names and today_only:
        date = dt.datetime.now().strftime(ui.DATE_FORMAT_YMD)
        for item in names:
            parts = item.split('_')
            if parts[0] == date:
                filenames = [item]
                break
    else:
        filenames = names

    return bool(filenames)


def dump(object: object, name: str, type: str) -> str:
    if not name:
        raise AssertionError('Must include \'name\'')
    if not type:
        raise AssertionError('Must include \'type\'')

    name = name.lower()
    type = type.lower()
    filename = build_filename(name, type)
    if filename:
        try:
            with open(filename, 'wb') as f:
                pickle.dump(object, f, protocol=pickle.HIGHEST_PROTOCOL)
                _logger.info(f'{__name__}: Results for {name}/{type} saved to cache')
        except Exception as e:
            filename = ''
            _logger.error(f'{__name__}: Exception for pickle dump: {str(e)}')

    return filename


def load(name: str, type: str, today_only: bool = True) -> tuple[object, str]:
    if not name:
        raise AssertionError('Must include \'name\'')
    if not type:
        raise AssertionError('Must include \'type\'')

    name = name.lower()
    type = type.lower()

    object = None
    filename = ''
    date = dt.datetime.now().strftime(ui.DATE_FORMAT_YMD)

    names = get_filenames(name, type)
    if not names:
        pass
    elif today_only:
        for item in names:
            parts = item.split('_')
            if parts[0] == date:
                filename = item
                break
    else:
        filename = names[0] # The latest file
        parts = filename.split('_')
        date = parts[0]

    if filename:
        filename = f'{CACHE_BASEPATH}/{filename}.{CACHE_SUFFIX}'
        try:
            with open(filename, 'rb') as f:
                object = pickle.load(f)
                _logger.info(f'{__name__}: Cached results for {name}/{type} available')
        except Exception as e:
            _logger.error(f'{__name__}: Exception for pickle load: {str(e)}')

    return object, date

def delete(type: str) -> tuple[bool, str]:
    if not type:
        raise AssertionError('Must include \'type\'')

    type = type.lower()
    success = True
    message = ''

    files = get_filenames('', type)
    if files:
        paths = []
        date = dt.datetime.now().strftime(ui.DATE_FORMAT_YMD)
        for path in files:
            head, sep, tail = path.partition('.')
            parts = head.split('_')
            file_date = f'{parts[0]}'
            if file_date != date:
                file = f'{CACHE_BASEPATH}/{path}.{CACHE_SUFFIX}'
                paths.append(file)

        if paths:
            deleted = 0
            for path in paths:
                try:
                    file = Path(path)
                    file.unlink()
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


def get_filenames(name: str, type: str, type_only: bool = False) -> list[str]:
    name = name.lower()
    type = type.lower()

    files = []
    path = Path(CACHE_BASEPATH)
    items = [item for item in path.glob(f'*.{CACHE_SUFFIX}') if item.is_file()]
    for item in items:
        head, sep, tail = item.name.partition('.')
        parts = head.split('_')

        if len(parts) != 3:
            pass # Bad filename structure
        elif name and name != parts[2]:
            pass # Bad name
        elif type == parts[1]:
            files.append(head)

    # Return most recent first
    files.sort(reverse=True)
    return files


def build_filename(name: str, type: str) -> str:
    if not name:
        raise ValueError('\'name\' must be valid')
    if not type:
        raise ValueError('\'type\' must be valid')

    name = name.lower()
    type = type.lower()
    date_time = dt.datetime.now().strftime(ui.DATE_FORMAT_YMD)
    filename = f'{CACHE_BASEPATH}/{date_time}_{type}_{name}.{CACHE_SUFFIX}'

    return filename


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 2:
        name = sys.argv[1]
        type = sys.argv[2]
    elif len(sys.argv) > 1:
        name = ''
        type = sys.argv[1]

    names = delete('scr')
