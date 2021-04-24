import logging
import math

import pandas as pd

def get_logger(level=None):
    logger = logging.getLogger('analysis')

    if level is not None:
        logger.handlers = []
    else:
        level = logging.WARNING

    if not logger.handlers:
        logger.propagate = 0 # Prevent logging from propagating to the root logger
        logger.setLevel(level)
        cformat = logging.Formatter('%(levelname)s: %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(cformat)
        logger.addHandler(handler)

    return logger

def compress_table(table, rows, cols):
    if not isinstance(table, pd.DataFrame):
        raise AssertionError("'table' must be a Pandas DataFrame")
    else:
        srows, scols = table.shape

        if cols > 0 and cols < scols:
            # thin out cols
            step = int(math.ceil(scols/cols))
            end = table[table.columns[-2::]]        # Save the last two cols
            table = table[table.columns[:-2:step]]  # Thin the table (less the last two cols)
            table = pd.concat([table, end], axis=1) # Add back the last two cols

        if rows > 0 and rows < srows:
            # Thin out rows
            step = int(math.ceil(srows/rows))
            table = table.iloc[::step]

    return table

def mround(n, precision):
    val = round(n / precision) * precision
    if val < 0.01: val = 0.01

    return val

def calc_major_minor_ticks(width):
    if width <= 0.0:
        major = 0
        minor = 0
    elif width > 1000:
        major = 100
        minor = 20
    elif width > 500:
        major = 50
        minor = 10
    elif width > 100:
        major = 10
        minor = 2
    elif width > 40:
        major = 5
        minor = 1
    elif width > 20:
        major = 2
        minor = 0
    elif width > 10:
        major = 1
        minor = 0
    elif width > 1:
        major = 0.5
        minor = 0
    else:
        major = .1
        minor = 0

    return major, minor


def menu(menu_items, header, minvalue, maxvalue):
    print(f'\n{header}')
    print('---------------------------------------------')

    option = menu_items.keys()
    for entry in option:
        print(f'{entry})\t{menu_items[entry]}')

    return input_integer('Please select: ', minvalue, maxvalue)

def delimeter(message, creturn=False):
    '''Common delimeter to bracket output'''
    if creturn:
        output = '\n'
    else:
        output = ''

    if len(message) > 0:
        output += f'***** {message} *****'
    else:
        output += '*****'

    return output

def input_integer(message, min_, max_):
    val = min_ - 1
    while val < min_:
        val = input(message)
        if val == '':
            val = min_ - 1
        elif not isnumeric(val):
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        elif int(val) < min_:
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        elif int(val) > max_:
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        else:
            val = int(val)

    return val

def input_float(message, min_, max_):
    val = min_ - 1
    while val < min_:
        val = input(message)
        if val == '':
            val = min_ - 1
        elif not isnumeric(val):
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        elif float(val) < min_:
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        elif float(val) > max_:
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        else:
            val = float(val)

    return val

def input_text(message):
    val = input(message)
    if any(char.isdigit() for char in val):
        val = ''
        print_error('Symbol value must be all letters')

    return val


def isnumeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def print_message(message, creturn=True):
    print(delimeter(f'{message}', creturn))

def print_warning(message, creturn=True):
    print(delimeter(f'Warning: {message}', creturn))

def print_error(message, creturn=True):
    print(delimeter(f'Error: {message}', creturn))

position = 0
direction = 'f'
def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', end='\r', percent=False, reset=False):
    global position
    global direction

    if reset:
        position = 0
        direction = 'f'

    if total > 0:
        filled = int(length * iteration // total)
        bar = fill * filled + '-' * (length - filled)

        if percent:
            percent = ('{0:.' + str(decimals) + 'f}').format(100 * (iteration / float(total)))
            print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=end)
        else:
            print(f'\r{prefix} |{bar}| {iteration}/{total} {suffix}', end=end)

        if iteration == total:
            print()
    elif total < 0:
        if direction == 'f':
            if position < length:
                position += 1
            else:
                position -= 1
                direction = 'r'
        else:
            if position > 1:
                position -= 1
            else:
                position = 2
                direction = 'f'

        front = position - 1
        back = length - position
        bar = ('-' * front) + fill + ('-' * back)

        print(f'\rWorking |{bar}| ', end=end)

if __name__ == '__main__':
    import time

    while(True):
        time.sleep(0.05)
        progress_bar(0, -1, 'Progress', 'Completed', length=50)
