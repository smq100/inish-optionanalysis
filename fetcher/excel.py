import pandas as pd

from .sheet import Sheet
from utils import utils as u

logger = u.get_logger()

class Excel(Sheet):
    def __init__(self, sheet_name):
        super().__init__(sheet_name)

    def open(self, tab):
        self.sheet = None
        self.opened = False
        if tab:
            self.tab = tab

            try:
                pd.read_excel(self.spreadsheet, sheet_name=self.tab, index_col=0)
            except FileNotFoundError as e:
                logger.debug(f'{__name__}: Unable to open file {self.spreadsheet}/{self.tab}')
                self.result = f'File not found: {e}'
            else:
                logger.info(f'{__name__}: Opened file {self.spreadsheet}/{self.tab}')
                self.opened = True

        return self.opened

    def get_column(self, column):
        self.col = []
        column -= 1
        if self.opened and column >= 0:
            self.col = pd.read_excel(self.spreadsheet, sheet_name=self.tab, index_col=column).index.tolist()

        return self.col

if __name__ == '__main__':
    xl = Excel()
    xl.open('TEST')
    xl.get_column(0)
    print(xl.col)
