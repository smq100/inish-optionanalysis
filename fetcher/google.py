'''
https://gspread.readthedocs.io/en/latest/
'''

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from .sheet import Sheet
from utils import utils as u


logger = u.get_logger()


class Google(Sheet):
    def __init__(self, sheet_name):
        super().__init__(sheet_name)

    def open(self, tab):
        self.sheet = None
        self.opened = False
        if tab:
            self.tab = tab

            scope = [
                # 'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/spreadsheets',
                # "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive"
            ]

            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name('fetcher/google.json', scope)
                client = gspread.authorize(creds)
                sheet = client.open(self.spreadsheet)
                self.sheet = sheet.worksheet(self.tab)
            except gspread.exceptions.SpreadsheetNotFound:
                logger.debug(f'{__name__}: Unable to open file {self.spreadsheet}/{self.tab}')
                self.result = '<File not found>'
            except Exception as e:
                logger.error(f'{__name__}: Error opening file {self.spreadsheet}/{self.tab}')
                self.result = '<An error occured>'
            else:
                logger.info(f'{__name__}: Opened file {self.spreadsheet}/{self.tab}')
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
