import pandas as pd

from fetcher.google import Google
from fetcher.excel import Excel

from fetcher import fetcher as f
from utils import utils as u

VALID_LISTS = ('SP500', 'DOW', 'NASDAQ', 'TEST')
VALID_TYPES = ('google', 'excel')
GOOGLE_SHEETNAME = 'Symbols'
EXCEL_SHEETNAME = 'data/symbols/symbols.xlsx'

logger = u.get_logger()

class History:
    def __init__(self, table_name='', table_type='google', days=365):
        table_name = table_name.upper()
        if table_name:
            if table_name not in VALID_LISTS:
                raise ValueError(f'Table not found: {table_name}')

        if table_type:
            if table_type not in VALID_TYPES:
                raise ValueError(f'Table type not valid: {table_name}')

        if days < 30:
            raise ValueError('Invalid number of days')
        self.days = days
        self.table_name = table_name
        self.table_type = table_type
        self.symbols = []
        self.items_total = 0
        self.items_completed = 0
        self.active_symbol = ''

        if table_type == 'google':
            self.table = Google(GOOGLE_SHEETNAME)
        elif table_type == 'excel':
            self.table = Excel(EXCEL_SHEETNAME)
        else:
            raise ValueError('Invalid table type')

        self._open()

    def refresh(self):
        if self.items_total <= 0:
            self._open()

        if self.items_total > 0:
            f.initialize()
            for symbol in self.symbols:
                f.refresh_history(symbol, self.days)

    def get_close(self):
        df_close = pd.DataFrame()
        print(len(self.symbols))
        if self.items_total > 0:
            for symbol in self.symbols:
                df = f.get_history(symbol, 365)
                df.set_index('Date')
                df.rename(columns={'Close': symbol}, inplace=True)
                df.drop(['Open','High','Low','Volume','Dividends','Stock Splits'], 1, inplace=True)

                if df_close.empty:
                    df_close = df
                else:
                    df_close = df_close.merge(df, how='outer')

        return df_close

    def _open(self):
        self.active_symbol = ''
        if self.table_name in VALID_LISTS:
            if self.table.open(self.table_name):
                self.symbols = self.table.get_column(1)
                self.items_total = len(self.symbols)
            else:
                self.error = 'Unable to open spreadsheet'
        else:
            self.error = 'Invalid table name'

        return self.items_total > 0


if __name__ == '__main__':
    # from logging import DEBUG
    # logger = u.get_logger(DEBUG)

    history = History('DOW')
    # history.refresh()
    close = history.get_close()
    print(close)
