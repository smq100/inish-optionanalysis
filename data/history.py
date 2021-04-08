import sqlite3 as sql
import pandas as pd

from fetcher.google import Google
from fetcher.excel import Excel

from fetcher import fetcher as f
from utils import utils as u

VALID_LISTS = ('SP500', 'DOW', 'NASDAQ', 'TEST')
VALID_TYPES = ('google', 'excel')

SQLITE_DIR = 'data'
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
        self.db_name = f'{SQLITE_DIR}/{self.table_name.lower()}.db'
        self.db = None
        self.symbols = []

        if table_type == 'google':
            self.table = Google(GOOGLE_SHEETNAME)
        elif table_type == 'excel':
            self.table = Excel(EXCEL_SHEETNAME)
        else:
            raise ValueError('Invalid table type')

        self._open()

    def get_close(self, refresh=False):
        df_close = pd.DataFrame()
        if not refresh:
            self.db = sql.connect(self.db_name)
            df_close = pd.read_sql_query("SELECT * from close", self.db)
            self.db.close()
        elif self.items > 0:
            for symbol in self.symbols:
                df = f.get_history(symbol, self.days)
                df.rename(columns={'Close':symbol}, inplace=True)
                df.drop(['Open', 'High', 'Low', 'Volume', 'Dividends', 'Stock Splits'], 1, inplace=True)

                if df_close.empty:
                    df_close = df
                else:
                    df_close = df_close.join(df, how='outer')

            if not df_close.empty:
                self.db = sql.connect(self.db_name)
                df_close.to_sql('close', self.db, if_exists='replace')
                self.db.close()

        return df_close

    @property
    def items(self):
        return len(self.symbols)

    def _open(self):
        if self.table_name in VALID_LISTS:
            if self.table.open(self.table_name):
                self.symbols = self.table.get_column(1)
            else:
                self.error = 'Unable to open spreadsheet'
        else:
            self.error = 'Invalid table name'

        return self.items > 0


if __name__ == '__main__':
    # from logging import DEBUG
    # logger = u.get_logger(DEBUG)

    f.initialize()
    history = History('DOW')
    h = history.get_close()
    print(h)
