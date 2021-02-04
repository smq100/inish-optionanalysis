'''TODO'''
import logging

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

def print_error(message, creturn=False):
    print(delimeter(f'Error: {message}', creturn))
