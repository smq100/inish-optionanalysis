import datetime, time

from analysis.technical import TechnicalAnalysis
from pricing.symbol import Symbol
from .sheets import Sheets
from utils import utils as u


logger = u.get_logger()

VALID_LISTS = ['SP500', 'DOW', 'NASDAQ', 'TEST']
VALID_SCREENS = ['test', 'minervini']


class Screener:
    def __init__(self, list_name):
        if list_name.upper() in VALID_LISTS:
            self.table_name = ''
            self.screen_name = ''
            self.table = Sheets()
            self.symbols = None
            self.items_total = 0
            self.items_completed = 0
            self.results = {}
            if self._open_table(list_name):
                self.table_name = list_name.upper()
                self.screen_name = VALID_SCREENS[0]

    def __str__(self):
        return self.table_name

    def run_screen(self, screen):
        self.results = []
        if screen.lower() == VALID_SCREENS[0]:
            self.screen_name = VALID_SCREENS[0]
            self.items_total = len(self.symbols)
            self.items_completed = 0
            self.results = self._process_test()
        elif screen.lower() == VALID_SCREENS[1]:
            self.screen_name = VALID_SCREENS[1]
            self.items_total = len(self.symbols)
            self.items_completed = 0
            self.results = self._process_minervini()

        return self.results

    def valid(self):
        return bool(self.table_name)

    def _open_table(self, table):
        if table in VALID_LISTS:
            if self.table.open(table):
                self.table_name = table
                self.symbols = self.table.get_column(1)
                self.items_total = len(self.symbols)
                self.items_completed = 0
            else:
                self.table_name = ''

        return bool(self.table_name)

    def _process_test(self):
        results = []
        if self.screen_name == VALID_SCREENS[0]:
            start = datetime.datetime.today() - datetime.timedelta(days=30)
            for s in self.symbols:
                try:
                    ta = TechnicalAnalysis(s, start)
                    price = ta.get_current_price()

                    # Condition 1: The current stock price is above a value
                    if price > 150.0:
                        results += [Symbol(s)]

                    self.items_completed += 1
                    time.sleep(0.1)
                except ValueError:
                    self.items_completed += 1
                    time.sleep(0.1)

        return results

    def _process_minervini(self):
        return []

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

    screener = Screener('sp500')
    c = screener.list.get_cell(1,1)
    print(c)
