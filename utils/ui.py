import os
import time
import re

from colorama import Fore, Style

from utils import math as m
from data import store as store


DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT2 = '%m-%d-%Y'
TABULATE_FORMAT = 'simple'
CHART_STYLE = 'seaborn-bright'
CHART_SIZE = (17, 10)
PROGRESS_SLEEP = 0.20

TERMINAL_SIZE = os.get_terminal_size()

# Globals for progress bar
_completed = 0
_position = 0
_forward = True
_start = 0.0


def menu(menu_items: dict, header: str, minvalue: int, maxvalue: int, prompt: str = 'Select operation') -> int:
    print(f'\n{header}')
    print('-' * 50)

    for entry in menu_items.keys():
        if entry.isnumeric():
            print(f'{entry:>2})\t{menu_items[entry]}')
        else:
            print(f'\t{menu_items[entry]}')

    return input_integer(f'{prompt}', minvalue, maxvalue)


def delimeter(message, pre_creturn: int, post_creturn: int) -> str:
    if pre_creturn > 0:
        output = '\n' * pre_creturn
    else:
        output = ''

    if len(message) > 0:
        output += f'***** {message} *****'
    else:
        output += '*****'

    if post_creturn > 0:
        output += '\n' * post_creturn

    return output


def print_message(message: str, pre_creturn: int = 1, post_creturn: int = 0) -> None:
    print(delimeter(message, pre_creturn, post_creturn))


def print_warning(message: str, pre_creturn: int = 1, post_creturn: int = 0) -> None:
    print(Fore.RED, end='')
    print(delimeter(f'Warning: {message}', pre_creturn, post_creturn))
    print(Style.RESET_ALL, end='')


def print_error(message: str, pre_creturn: int = 1, post_creturn: int = 0) -> None:
    print(Fore.RED, end='')
    print(delimeter(f'Error: {message}', pre_creturn, post_creturn))
    print(Style.RESET_ALL, end='')


def print_tickers(tickers: list[str], group: int = 15) -> None:
    if group < 2:
        raise ValueError('Invalid grouping value')

    index = 0
    if len(tickers) > 0:
        for ticker in tickers:
            print(f'{ticker} ', end='')
            index += 1
            if index % group == 0:
                print()
        print()


def erase_line() -> None:
    global _position, _forward

    _position = 0
    _forward = True
    erase = TERMINAL_SIZE.columns * ' '
    print(f'{erase}', end='\r')


def format_headers(columns: str, case: str = 'title'):
    if case == 'upper':
        header = [header.replace('_', '\n').upper() for header in columns]
    elif case == 'lower':
        header = [header.replace('_', '\n').lower() for header in columns]
    else:
        header = [header.replace('_', '\n').title() for header in columns]

    return header


def convert(camel_case: str) -> str:
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    name = pattern.sub('_', name).lower()

    return name


def input_integer(message: str, min_: int, max_: int) -> int:
    val = min_ - 1
    while val < min_:
        text = input(f'{message}: ')
        if m.isnumeric(text):
            val = int(text)
            if val < min_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            elif val > max_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            else:
                val = val
        else:
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1

    return val


def input_float(message: str, min_: float, max_: float) -> float:
    val = min_ - 1.0
    while val < min_:
        text = input(f'{message}: ')
        if m.isnumeric(text):
            val = int(text)
            if float(val) < min_:
                print_error(f'Invalid value. Enter an integer between {min_:.2f} and {max_:.2f}')
                val = min_ - 1.0
            elif float(val) > max_:
                print_error(f'Invalid value. Enter an integer between {min_:.2f} and {max_:.2f}')
                val = min_ - 1.0
            else:
                val = float(val)
        else:
            print_error(f'Invalid value. Enter an integer between {min_:.2f} and {max_:.2f}')
            val = min_ - 1.0

    return val


def input_float_range(message: str, middle: float, percent: float) -> float:
    if percent < 1.0:
        percent = 1.0
    elif percent > 100.0:
        percent = 100.0

    percent /= 100.0
    min_ = middle * (1.0 - percent)
    max_ = middle * (1.0 + percent)

    return input_float(message, min_, max_)


def input_text(message: str) -> str:
    val = input(f'{message}: ')
    if not all(char.isalpha() for char in val):
        val = ''
        print_error('Symbol value must be all letters')

    return val


def input_list(message: str, separator: str = ',') -> str:
    val = input(f'{message}: ').replace(' ', '')
    if not all(char.isalpha() or char == separator for char in val):
        val = ''
        print_error('Symbol value must be all letters')

    return val


def input_alphanum(message: str) -> str:
    val = input(f'{message}: ')
    if not all(char.isalnum() for char in val):
        val = ''
        print_error('Symbol value must be all letters')

    return val


def input_yesno(message: str) -> bool:
    return input(f'{message} (y/n)? ').lower() == 'y'


def input_table(exchange: bool = False, index: bool = False, ticker: bool = False, all: bool = False) -> str:
    if exchange and index and ticker:
        prompt = 'Enter an exchange, an index or a ticker'
    elif exchange and index and not ticker:
        prompt = 'Enter an exchange or an index'
    elif exchange and not index and ticker:
        prompt = 'Enter an exchange or a ticker'
    elif not exchange and index and ticker:
        prompt = 'Enter an index or a ticker'
    elif exchange and not index and not ticker:
        prompt = 'Enter an exchange'
    elif not exchange and index and not ticker:
        prompt = 'Enter an index'
    elif not exchange and not index and ticker:
        prompt = 'Enter a ticker'
    else:
        assert ValueError('Invalid options')

    prompt += ' (or \'every\')' if all else ''

    while True:
        table = input_alphanum(prompt).upper()

        if not table:
            break
        elif all and table == 'EVERY':
            break
        elif all and table == 'BOGUS':
            break
        elif exchange and store.is_exchange(table):
            break
        elif index and store.is_index(table):
            break
        elif ticker and store.is_ticker(table):
            break
        else:
            print_error('Table not found. Enter a valid table, or return to exit')

    return table


def progress_bar(iteration, total: int, prefix: str = 'Working', suffix: str = '', ticker: str = '',
                 length: int = 50, fill='█', success: int = -1, tasks: int = 0, reset: bool = False) -> None:

    global _completed, _position, _forward, _start

    if reset:
        _completed = 0
        _position = 0
        _forward = True
        _start = time.perf_counter()
        erase_line()

    if total > 0:
        filled = int(length * iteration // total)
        bar = (fill * filled) + ('-' * (length - filled))

        elapsed = time.perf_counter() - _start
        if _completed > 5:
            per = elapsed / _completed
            remaining = per * (total - iteration)
            minutes, seconds = divmod(remaining, 60)
            hours, minutes = divmod(minutes, 60)
        else:
            hours = 0.0
            minutes = 0.0
            seconds = 0.0

        if iteration == _completed:
            pass  # Nothing new to show
        elif success < 0:
            print(f'{prefix:<13} |{bar}| {iteration}/{total} {suffix} {ticker}     ', end='\r')
        elif tasks > 0:
            print(f'{prefix:<13} |{bar}| {success}/{iteration}/{total} [{tasks}] {ticker:<5} {hours:02.0f}:{minutes:02.0f}:{seconds:02.0f} {suffix}     ', end='\r')
        else:
            print(f'{prefix:<13} |{bar}| {success}/{iteration}/{total} {ticker:<5} {hours:02.0f}:{minutes:02.0f}:{seconds:02.0f} {suffix}     ', end='\r')

        _completed = iteration

    else:  # Use oscillating marker when the total is not known
        if _forward:
            if _position < length:
                _position += 1
            else:
                _position -= 1
                _forward = False
        elif _position > 1:
            _position -= 1
        else:
            _position = 2
            _forward = True

        front = _position - 1
        back = length - _position
        bar = ('-' * front) + fill + ('-' * back)

        print(f'{prefix} |{bar}| {suffix}             ', end='\r')


if __name__ == '__main__':
    print(input_table(exchange=False, index=False, ticker=False))
