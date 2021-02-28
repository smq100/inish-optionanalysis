import logging
import math

import numpy as np
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

def menu(menu_items, header, minvalue, maxvalue):
    print(f'\n{header}')
    print('-----------------------------')

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

def isnumeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def print_message(message, creturn=False):
    print(delimeter(f'{message}', creturn))

def print_warning(message, creturn=False):
    print(delimeter(f'Warning: {message}', creturn))

def print_error(message, creturn=False):
    print(delimeter(f'Error: {message}', creturn))
