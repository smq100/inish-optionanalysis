import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils import utils as u


logger = u.get_logger()


class Sheets:
    def __init__(self):
        self.opened = False
        self.spreadsheet = 'Symbols'
        self.tab = ''
        self.sheet = None
        self.result = ''
        self.row = 0
        self.col = 0

    def __str__(self):
        return self.spreadsheet

    def open(self, tab):
        if tab:
            self.tab = tab
            self.sheet = None
            self.opened = False

        scope = [
            # 'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            # "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]

        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            sheet = client.open(self.spreadsheet)
            self.sheet = sheet.worksheet(self.tab)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.debug(f'{__name__}: Unable to open file {self.spreadsheet}/{self.tab}')
            self.result = '<File not found>'
        except:
            logger.error(f'{__name__}: Error opening file {self.spreadsheet}/{self.tab}')
            self.result = '<An error occured>'
        else:
            logger.info(f'{__name__}: Opened file {self.spreadsheet}/{self.tab}')
            self.opened = True

        return self.opened

    def get_column(self, column):
        col = []
        if self.opened and column > 0:
            col = self.sheet.col_values(column)

        return col

    def get_cell(self, row, col):
        if self.opened:
            self.row = row
            self.col = col
            self.result = self.sheet.cell(self.row, self.col).value
        else:
            self.result = '<File not open>'

        return self.result

    def update_cell(self, value, row, col):
        if self.opened:
            self.row = row
            self.col = col
            self.sheet.update_cell(self.row, self.col, value)
            self.result = self.sheet.cell(self.row, self.col).value

            # data = sheet.get_all_records()  # Get a list of all records
            # row = sheet.row_values(3)  # Get a specific row
            # col = sheet.col_values(3)  # Get a specific column
            # cell = sheet.cell(1,2).value  # Get the value of a specific cell
            # insertRow = ["hello", 5, "red", "blue"]
            # sheet.add_rows(insertRow, 4)  # Insert the list as a row at index 4
            # numRows = sheet.row_count  # Get the number of rows in the sheet
