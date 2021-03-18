import os, datetime, time, json

from .sheets import Sheets
from .interpreter import Interpreter, SyntaxError
from pricing.symbol import Symbol
from pricing import fetcher as f
from utils import utils as u


logger = u.get_logger()

VALID_LISTS = ('SP500', 'DOW', 'NASDAQ', 'TEST')


class Screener:
    def __init__(self, list_name, script=None, days=365):
        list_name = list_name.upper()
        if list_name not in VALID_LISTS:
            raise ValueError('Invalid list')
        if days < 30:
            raise ValueError('Invalid number of days')

        self.days = days
        self.table_name = ''
        self.table = Sheets()
        self.script = []
        self.symbols = []
        self.items_total = 0
        self.items_completed = 0
        self.results = []
        self.error = ''

        if self._open_table(list_name):
            self.table_name = list_name

        if script is not None:
            self.load_script(script)

    def __str__(self):
        return self.table_name

    class Result:
        def __init__(self, symbol, result):
            self.symbol = symbol
            self.values = result

        def __str__(self):
            return self.symbol

        def __bool__(self):
            return all(self.values)

    def load_script(self, script):
        self.script = None
        if os.path.exists(script):
            try:
                with open(script) as f:
                    self.script = json.load(f)
                    valid = True
            except:
                logger.error(f'{__name__}: File format error')
        else:
            logger.warning(f'{__name__}: File "{script}" not found')

        return self.script is not None

    def run_script(self):
        self.results = []
        self.items_completed = 0
        if len(self.symbols) == 0:
            self.items_completed = self.items_total
            self.results = []
            logger.warning(f'{__name__}: No symbols')
        elif len(self.script) == 0:
            self.items_completed = self.items_total
            self.results = []
            logger.error(f'{__name__}: Illegal script')
        else:
            for symbol in self.symbols:
                result = []
                for condition in self.script:
                    i = Interpreter(symbol, condition)
                    try:
                        result += [i.run()]
                    except SyntaxError as e:
                        self.error = str(e)
                        break

                if not self.error:
                    self.items_completed += 1
                    self.results += [self.Result(symbol.ticker, result)]
                else:
                    self.items_completed = self.items_total
                    self.results = []
                    break

        return self.results

    def valid(self):
        return bool(self.table_name)

    def _open_table(self, table):
        table = table.upper()
        self.table_name = ''
        self.items_total = 0
        self.items_completed = 0
        if table in VALID_LISTS:
            if self.table.open(table):
                self.table_name = table
                symbols = self.table.get_column(1)
                for s in symbols:
                    if f.validate_ticker(s):
                        self.symbols += [Symbol(s, self.days)]
                    else:
                        logger.warning(f'{__name__}: Invalid ticker {s}')

                self.items_total = len(self.symbols)

        return self.items_total > 0


    # Minevini
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
    u.get_logger(logging.DEBUG)

    s = Screener('test')
    s.load_script('/Users/steve/Documents/Source Code/Personal/OptionAnalysis/screener/scripts/test1.script')
    s.run_script()
