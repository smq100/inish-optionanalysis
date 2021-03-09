from .sheets import Sheets
from utils import utils as u


logger = u.get_logger()


class Screener:
    def __init__(self, table_name):
        self.sheet = Sheets()
        self.table_name = table_name
        self.symbols = None
        self.valid = False

        self.open_table(self.table_name)

    def open_table(self, table=None):
        self.valid = False
        if table is None:
            if self.sheet.open(self.table_name):
                self.valid = True
        elif self.sheet.open(table):
            self.valid = True

        return self.valid

    def get_symbols(self):
        if self.valid:
            self.symbols = self.sheet.sheet.col_values(1)
        else:
            raise AssertionError('Invalid table')

        return self.symbols


if __name__ == '__main__':
    import logging
    u.get_logger(logging.DEBUG)

    screener = Screener()
    screener.sheet.open('SP500')
    c = screener.sheet.lookup_cell(10,1)
    print(c)