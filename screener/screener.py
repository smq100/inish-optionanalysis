import os
import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from base import Threaded
from company.company import Company
from utils import utils as utils
from data import store as o
from .interpreter import Interpreter


logger = utils.get_logger()

class Screener(Threaded):
    def __init__(self, table, script='', days=365, live=False):
        super().__init__()

        table = table.upper()
        self.type = ''

        if table:
            if o.is_exchange(table):
                self.type = 'exchange'
            elif o.is_index(table):
                self.type = 'index'
            else:
                raise ValueError(f'Table not found: {table}')
        else:
            raise ValueError('Must specify a table name')

        if days < 30:
            raise ValueError('Invalid number of days')

        self.days = days
        self.live = live
        self.table = table
        self.script = []
        self.symbols = []
        self.results = []

        if script:
            if not self.load_script(script):
                raise ValueError(f'Script not found: {script}')

        self.open()

    def __str__(self):
        return self.table

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
        self.items_error = ''
        symbols = []

        if self.type == 'exchange':
            symbols = o.get_exchange_symbols(self.table)
        elif self.type == 'index':
            symbols = o.get_index_symbols(self.table)
        else:
            self.items_error = 'Invalid table name'

        if len(symbols) > 0:
            self.items_total = len(symbols)
            for s in symbols:
                try:
                    self.symbols += [Company(s, self.days, live=self.live)]
                except ValueError as e:
                    logger.warning(f'{__name__}: Invalid ticker {s}')

                self.items_completed += 1

            self.items_total = len(self.symbols)
            logger.debug(f'{__name__}: Opened {self.items_total} symbols from {self.table} table')
        else:
            logger.debug(f'{__name__}: No symbols available')
            self.items_error = 'No symbols'

        return self.items_total > 0

    def load_script(self, script):
        self.script = None
        if os.path.exists(script):
            try:
                with open(script) as f:
                    self.script = json.load(f)
            except:
                self.script = None
                logger.error(f'{__name__}: File format error')
        else:
            logger.warning(f'{__name__}: File "{script}" not found')

        return self.script is not None

    @Threaded.threaded
    def run_script(self):
        self.results = []
        self.items_total = len(self.symbols)

        if self.items_total == 0:
            self.items_completed = self.items_total
            self.results = []
            self.items_error = 'No symbols'
            logger.warning(f'{__name__}: {self.items_error}')
        elif len(self.script) == 0:
            self.items_completed = self.items_total
            self.results = []
            self.items_error = 'Illegal script'
            logger.warning(f'{__name__}: {self.items_error}')
        else:
            self.items_error = 'None'

            # Split the list and remove any empty lists
            lists = np.array_split(self.symbols, 3)
            lists = [i for i in lists if i is not None]

            with ThreadPoolExecutor() as executor:
                futures = executor.map(self._run, lists)

            for future in futures:
                if future is None:
                    self.items_results += ['Ok']
                else:
                    self.items_results += [future.result()]

        return self.results

    def _run(self, tickers):
        for symbol in tickers:
            result = []
            self.items_symbol = symbol
            for condition in self.script:
                i = Interpreter(symbol, condition)
                try:
                    result += [i.run()]
                except SyntaxError as e:
                    self.items_error = str(e)
                    break
                except RuntimeError as e:
                    self.items_error = str(e)
                    break

            if self.items_error == 'None':
                self.items_completed += 1
                self.results += [self.Result(symbol, result)]
                if (bool(self.results[-1])):
                    self.items_success += 1
            else:
                self.items_completed = self.items_total
                self.results = []
                break

    def valid(self):
        return bool(self.table)


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
    from fetcher import fetcher as fetcher

    utils.get_logger(logging.DEBUG)

    s = Screener('DOW')
    s.load_script('/Users/steve/Documents/Source Code/Personal/OptionAnalysis/screener/screens/test.screen')
    # s.run_script()
