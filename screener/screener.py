from .sheets import Sheets
from utils import utils as u


logger = u.get_logger()

VALID_LISTS = ('SP500', 'DOW', 'NASDAQ')


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

    def valid(self):
        return bool(self.list_name)

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
