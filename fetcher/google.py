'''
https://github.com/burnash/gspread
'''

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from .sheet import Sheet
from utils import utils as utils


_logger = utils.get_logger()

CREDENTIALS = 'fetcher/google.json'

class Google(Sheet):
    def __init__(self, sheet_name):
        super().__init__(sheet_name)

    def open(self, tab):
        self.sheet = None
        self.opened = False
        if tab:
            self.tab_name = tab

            scope = [
                # 'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/spreadsheets',
                # "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive"
            ]

            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS, scope)
                client = gspread.authorize(creds)
                sheet = client.open(self.sheet_name)
                self.sheet = sheet.worksheet(self.tab_name)
            except gspread.exceptions.SpreadsheetNotFound:
                _logger.error(f'{__name__}: Unable to open file {self.sheet_name}/{self.tab_name}')
            except Exception as e:
                _logger.error(f'{__name__}: Error opening file {self.sheet_name}/{self.tab_name}')
            else:
                _logger.info(f'{__name__}: Opened file {self.sheet_name}/{self.tab_name}')
                self.opened = True

        return self.opened

    def get_column(self, column):
        col = []
        if self.opened and column > 0:
            self.col = self.sheet.col_values(column)

        return self.col

if __name__ == '__main__':
    gs = Google('Symbols')
    gs.open('TEST')
    gs.get_column(1)
    print(gs.col)
