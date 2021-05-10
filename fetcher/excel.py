
'''
https://github.com/chronossc/openpyxl
'''

from openpyxl import load_workbook

from .sheet import Sheet
from utils import utils as utils

_logger = utils.get_logger()

COLUMNS = ['','A','B','C','D','E','F']

class Excel(Sheet):
    def __init__(self, sheet_name):
        super().__init__(sheet_name)

    def open(self, tab):
        self.sheet = None
        self.opened = False
        if tab:
            self.tab_name = tab

            try:
                wb = load_workbook(filename=self.sheet_name, data_only=True)
                self.sheet = wb[self.tab_name]
            except Exception as e:
                _logger.debug(f'{__name__}: Unable to open file {self.sheet_name}/{self.tab_name}')
            else:
                _logger.info(f'{__name__}: Opened file {self.sheet_name}/{self.tab_name}')
                self.opened = True

        return self.opened

    def get_column(self, column):
        self.col = []
        if self.opened and column > 0:
            col = self.sheet[COLUMNS[column]]
            for cell in col:
                self.col += [cell.value]

        return self.col

if __name__ == '__main__':
    xl = Excel('data/symbols/symbols.xlsx')
    xl.open('TEST')
    xl.get_column(1)
    print(xl.col)
