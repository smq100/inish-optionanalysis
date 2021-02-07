'''TODO'''
import logging
import re

import numpy as np


LOG_LEVEL = logging.WARNING


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


def parse_contract_name(contract_name):
    # ex: MSFT210305C00237500
    regex = r'([\d]{6})([PC])'
    parsed = re.split(regex, contract_name)

    ticker = parsed[0]
    expiry = f'20{parsed[1][:2]}-{parsed[1][2:4]}-{parsed[1][4:]}'
    strike = float(parsed[3][:5]) + float(parsed[3][5:]) / 1000.0

    if 'C' in parsed[2].upper():
        product = 'call'
    else:
        product = 'put'

    return {'ticker':ticker, 'expiry':expiry, 'product':product, 'strike':strike}


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
        if not _isnumeric(val):
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


def print_error(message, creturn=False):
    print(delimeter(f'Error: {message}', creturn))


def _isnumeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
