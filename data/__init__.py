SQLITE_DATABASE_PATH = 'data/securities.db'
SQLITE_URI = f'sqlite:///{SQLITE_DATABASE_PATH}'

VALID_SPREADSHEETS = ('google', 'excel')

GOOGLE_SHEETNAME_EXCHANGES = 'Exchanges'
GOOGLE_SHEETNAME_INDEXES = 'Indexes'
EXCEL_SHEETNAME_EXCHANGES = 'data/symbols/exchanges.xlsx'
EXCEL_SHEETNAME_INDEXES = 'data/symbols/indexes.xlsx'

EXCHANGES = ({'abbreviation':'NASDAQ', 'name':'National Association of Securities Dealers Automated Quotations'},
             {'abbreviation':'NYSE',   'name':'New York Stock Exchange'},
             {'abbreviation':'AMEX',   'name':'American Stock Exchange'})

INDEXES = ({'abbreviation':'SP500', 'name':'Standard & Poors 500'},
           {'abbreviation':'DOW',   'name':'DOW industrials'},
           {'abbreviation':'TEST',  'name':'Test Index'})
