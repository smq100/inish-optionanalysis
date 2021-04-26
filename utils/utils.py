import logging

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

def print_message(message, creturn=True):
    print(delimeter(f'{message}', creturn))

def print_warning(message, creturn=True):
    print(delimeter(f'Warning: {message}', creturn))

def print_error(message, creturn=True):
    print(delimeter(f'Error: {message}', creturn))

position = 0
direction = 'f'
def progress_bar(iteration, total, prefix='', suffix='', symbol='', decimals=1, length=100, fill='█', end='\r', percent=False, reset=False, success=-1):
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
            print(f'\r{prefix} |{bar}| {percent}% {suffix} {symbol}', end=end)
        elif success < 0:
            print(f'\r{prefix} |{bar}| {iteration}/{total} {suffix} {symbol}', end=end)
        else:
            print(f'\r{prefix} |{bar}| {iteration}/{total} ({success}) {suffix} {symbol}', end=end)

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

def mround(n, precision):
    val = round(n / precision) * precision
    if val < 0.01: val = 0.01

    return val

def isnumeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    import time

    while(True):
        time.sleep(0.05)
        progress_bar(0, -1, 'Progress', 'Completed', length=50)
