from .sheets import Sheets
from utils import utils as u


logger = u.get_logger()

VALID_LISTS = ['SP500', 'DOW', 'NASDAQ']
VALID_SCREENS = ['minervini']


class Screener:
    def __init__(self, table_name):
        if table_name.upper() in VALID_LISTS:
            self.list = Sheets()
            self.list_name = ''
            self.symbols = None
            if self._open_table(table_name):
                self.list_name = table_name.upper()

    def __str__(self):
        return self.list_name

    def run_screen(self, screen):
        located = []
        if screen.lower() == VALID_SCREENS[0]:
            located = self._process()

        return located

    def valid(self):
        return bool(self.list_name)

    def _process(self):
        return ['AAPL', 'WMT']


    # 1. The current stock price is above both the 150-day (30-week) and the 200-day (40-week) moving average price lines.
    # 2. The 150-day moving average is above the 200-day moving average.
    # 3. The 200-day moving average line is trending up for at least 1 month (preferably 4–5 months minimum in most cases).
    # 4. The 50-day (10-week) moving average is above both the 150-day and 200-day moving averages.
    # 5. The current stock price is trading above the 50-day moving average.
    # 6. The current stock price is at least 25% above its 52-week low (30% as per his book 'Trade Like a Stock Market Wizard').
    # 7. The current stock price is within at least 25% of its 52-week high (the closer to a new high the better).
    # 8. The Relative Strength ranking (RS ranking), as reported in Investor’s Business Daily, is no less than 70.


    def _open_table(self, table):
        if table in VALID_LISTS:
            if self.list.open(table):
                self.list_name = table
                self._get_symbols()
            else:
                self.list_name = ''

        return bool(self.list_name)

    def _get_symbols(self):
        if self.list_name:
            self.symbols = self.list.get_column(1)
        else:
            self.symbols = []

        return self.symbols


if __name__ == '__main__':
    import logging
    u.get_logger(logging.DEBUG)

    screener = Screener('sp500')
    c = screener.list.get_cell(1,1)
    print(c)
