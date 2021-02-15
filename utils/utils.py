'''TODO'''
import logging

import numpy as np


LOG_LEVEL = logging.DEBUG


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

def mround(n, precision):
    val = int(n / precision + 0.5) * precision
    if val < 0.01: val = 0.01
    return val


def input_integer(message, min_, max_):
    val = min_ - 1
    while val < min_:
        val = input(message)
        if not val.isnumeric():
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
        if not isnumeric(val):
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
