import os
import json

from company.company import Company
from utils import utils as u
from data import store as o
from .interpreter import Interpreter, SyntaxError

logger = u.get_logger()


class Screener:
    def __init__(self, table_name='', script_name='', days=365):
        table_name = table_name.upper()
        if table_name:
            if not o.is_index(table_name):
                raise ValueError(f'Table not found: {table_name}')

        if days < 30:
            raise ValueError('Invalid number of days')

        self.days = days
        self.table_name = table_name
        self.script = []
        self.symbols = []
        self.items_total = 0
        self.items_completed = 0
        self.results = []
        self.error = ''
        self.active_symbol = ''
        self.matches = 0

        if script_name:
            if not self.load_script(script_name):
                raise ValueError(f'Script not found: {script_name}')

    def __str__(self):
        return self.table_name

    class Result:
        def __init__(self, symbol, result):
            self.symbol = symbol
            self.values = result

        def __str__(self):
            return self.symbol.ticker

        def __bool__(self):
            return all(self.values)

    def open(self):
        self.items_total = 0
        self.items_completed = 0
        self.error = ''
        self.active_symbol = ''
        if o.is_index(self.table_name):
            symbols = o.get_index(self.table_name)
            self.items_total = len(symbols)
            self.error = 'None'
            for s in symbols:
                try:
                    self.symbols += [Company(s, self.days)]
                except ValueError as e:
                    logger.warning(f'{__name__}: Invalid ticker {s}')

                self.items_completed += 1

            self.items_total = len(self.symbols)
        else:
            self.error = 'Invalid table name'

        return self.items_total > 0

    def load_script(self, script):
        self.script = None
        if os.path.exists(script):
            try:
                with open(script) as f:
                    self.script = json.load(f)
                    valid = True
            except:
                self.script = None
                logger.error(f'{__name__}: File format error')
        else:
            logger.warning(f'{__name__}: File "{script}" not found')

        return self.script is not None

    def run_script(self):
        self.results = []
        self.items_completed = 0
        self.error = ''
        self.matches = 0

        if len(self.symbols) == 0:
            self.items_completed = self.items_total
            self.results = []
            self.error = 'No symbols'
            logger.warning(f'{__name__}: {self.error}')
        elif len(self.script) == 0:
            self.items_completed = self.items_total
            self.results = []
            self.error = 'Illegal script'
            logger.warning(f'{__name__}: {self.error}')
        else:
            self.error = 'None'
            for symbol in self.symbols:
                result = []
                for condition in self.script:
                    i = Interpreter(symbol, condition)
                    self.active_symbol = symbol.ticker
                    try:
                        result += [i.run()]
                    except SyntaxError as e:
                        self.error = str(e)
                        break

                if self.error == 'None':
                    self.items_completed += 1
                    self.results += [self.Result(symbol, result)]
                    if (bool(self.results[-1])):
                        self.matches += 1
                else:
                    self.items_completed = self.items_total
                    self.results = []
                    break

        return self.results

    def valid(self):
        return bool(self.table_name)


    # Minervini:
    # Condition 1: The current stock price is above both the 150-day (30-week) and the 200-day (40-week) moving average price lines.
    # Condition 2: The 150-day moving average is above the 200-day moving average.
    # Condition 3: The 200-day moving average line is trending up for at least 1 month (preferably 4–5 months minimum in most cases).
    # Condition 4: The 50-day (10-week) moving average is above both the 150-day and 200-day moving averages.
    # Condition 5: The current stock price is trading above the 50-day moving average.
    # Condition 6: The current stock price is at least 25% above its 52-week low (30% as per his book 'Trade Like a Stock Market Wizard').
    # Condition 7: The current stock price is within at least 25% of its 52-week high (the closer to a new high the better).
    # Condition 8: The Relative Strength ranking (RS ranking), as reported in Investor’s Business Daily, is no less than 70.


if __name__ == '__main__':
    import logging
    from fetcher import fetcher as f

    u.get_logger(logging.DEBUG)

    s = Screener('SP500')
    s.open()
    s.load_script('/Users/steve/Documents/Source Code/Personal/OptionAnalysis/screener/screens/test.screen')
    s.run_script()
