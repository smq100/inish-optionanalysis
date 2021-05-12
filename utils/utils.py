import logging

LOG_DIR = './log'


def get_logger(level=None):
    logger = logging.getLogger('analysis')

    if level is not None:
        logger.handlers = []
        logger.setLevel(logging.DEBUG)
        logger.propagate = 0 # Prevent logging from propagating to the root logger

        # Console handler
        cformat = logging.Formatter('%(levelname)s: %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(cformat)
        ch.setLevel(level)
        logger.addHandler(ch)

        # File handler
        fformat = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
        fh = logging.FileHandler(f'{LOG_DIR}/output.log', 'w+')
        fh.setFormatter(fformat)
        fh.setLevel(logging.INFO)
        logger.addHandler(fh)

    return logger

def menu(menu_items, header, minvalue, maxvalue):
    print(f'\n{header}')
    print('---------------------------------------------')

    [print(f'{entry:>2})\t{menu_items[entry]}') for entry in menu_items.keys()]

    return input_integer('Please select: ', minvalue, maxvalue)

def _delimeter(message, creturn):
    if creturn > 0:
        output = '\n' * creturn
    else:
        output = ''

    if len(message) > 0:
        output += f'***** {message} *****'
    else:
        output += '*****'

    return output

def print_message(message, creturn=1):
    print(_delimeter(f'{message}', creturn))

def print_warning(message, creturn=1):
    print(_delimeter(f'Warning: {message}', creturn))

def print_error(message, creturn=1):
    print(_delimeter(f'Error: {message}', creturn))

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

position = 0
direction = 'f'
def progress_bar(iteration, total, prefix='', suffix='', symbol='', decimals=1, length=100, fill='█', end='\r', percent=False, reset=False, success=-1, tasks=0):
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
            print(f'\r{prefix} |{bar}| {percent}% {suffix} {symbol}     ', end=end)
        elif success < 0:
            print(f'\r{prefix} |{bar}| {iteration}/{total} {suffix} {symbol}     ', end=end)
        else:
            print(f'\r{prefix} |{bar}| {iteration}/{total} ({success}) [{tasks}] {suffix} {symbol}     ', end=end)

        if iteration == total:
            print()
    else:
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

        print(f'\rWorking |{bar}| {suffix}', end=end)

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
