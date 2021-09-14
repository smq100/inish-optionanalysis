import logging
from logging import Logger

LOG_DIR = './log'


def get_logger(level:int=logging.WARNING, logfile:str='') -> Logger:
    logger = logging.getLogger('analysis')

    if logger is None:
        logger.handlers = []
        logger.setLevel(logging.DEBUG)
        logger.propagate = False # Prevent logging from propagating to the root logger

        # Console handler
        cformat = logging.Formatter('%(levelname)s: %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(cformat)
        ch.setLevel(level)
        logger.addHandler(ch)

        # File handler
        if logfile:
            fformat = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
            fh = logging.FileHandler(f'{LOG_DIR}/{logfile}.log', 'w+')
            fh.setFormatter(fformat)
            fh.setLevel(logging.DEBUG)
            logger.addHandler(fh)

    return logger

def menu(menu_items:dict, header:str, minvalue:int, maxvalue:int) -> int:
    print(f'\n{header}')
    print('-' * 50)

    [print(f'{entry:>2})\t{menu_items[entry]}') for entry in menu_items.keys()]

    return input_integer('Please select: ', minvalue, maxvalue)

def _delimeter(message, creturn:int=0) -> str:
    if creturn > 0:
        output = '\n' * creturn
    else:
        output = ''

    if len(message) > 0:
        output += f'***** {message} *****'
    else:
        output += '*****'

    return output

def print_message(message:str, creturn:int=1) -> None:
    print(_delimeter(f'{message}', creturn))

def print_warning(message:str, creturn:int=1) -> None:
    print(_delimeter(f'Warning: {message}', creturn))

def print_error(message:str, creturn:int=1) -> None:
    print(_delimeter(f'Error: {message}', creturn))

def print_line(message:str, creturn:int=1) -> None:
    print(_delimeter(message, creturn))

def input_integer(message:str, min_:int, max_:int) -> int:
    val = min_ - 1
    while val < min_:
        text = input(message)
        if not isnumeric(text):
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        else:
            val = int(text)
            if val < min_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            elif val > max_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            else:
                val = val

    return val

def input_float(message:str, min_:float, max_:float) -> float:
    val = min_ - 1
    while val < min_:
        text = input(message)
        if not isnumeric(text):
            print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
            val = min_ - 1
        else:
            val = int(text)
            if float(val) < min_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            elif float(val) > max_:
                print_error(f'Invalid value. Enter an integer between {min_} and {max_}')
                val = min_ - 1
            else:
                val = float(val)

    return val

def input_text(message:str) -> str:
    val = input(message)
    if any(char.isdigit() for char in val):
        val = ''
        print_error('Symbol value must be all letters')

    return val

completed = 0
position = 0
forward = True
def progress_bar(iteration, total:int, prefix:str='', suffix:str='', ticker:str='',
    length:int=100, fill:str='█', reset:bool=False, success:int=-1, tasks:int=0) -> None:
    global completed
    global position
    global forward

    if reset:
        completed = 0
        position = 0
        forward = True

    if total > 0:
        filled = int(length * iteration // total)
        bar = fill * filled + '-' * (length - filled)

        if iteration == completed:
            pass
        elif success < 0:
            print(f'\r{prefix} |{bar}| {iteration}/{total} {suffix} {ticker}     ', end='\r')
        else:
            print(f'\r{prefix} |{bar}| {iteration}/{total} ({success}) [{tasks}] {suffix} {ticker}     ', end='\r')

        completed = iteration

        if iteration == total:
            print()
    else: # Use oscillating marker when the total is not known
        if forward:
            if position < length:
                position += 1
            else:
                position -= 1
                forward = False
        else:
            if position > 1:
                position -= 1
            else:
                position = 2
                forward = True

        front = position - 1
        back = length - position
        bar = ('-' * front) + fill + ('-' * back)

        print(f'\rWorking |{bar}| {suffix}', end='\r')

def mround(n, precision:float) -> float:
    val = float(round(n / precision) * precision)
    if val < 0.01: val = 0.01

    return val

def isnumeric(value) -> bool:
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
