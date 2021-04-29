import configparser

CREDENTIALS = './data/postgres.ini'
config = configparser.ConfigParser()
config.read(CREDENTIALS)
dbuser = config['DEFAULT']['USER']
dbpw = config['DEFAULT']['PW']
port = config['DEFAULT']['PORT']
db = config['DEFAULT']['DB']

OPTIONS_DB = ('Postgres', 'SQLite')
ACTIVE_DB = OPTIONS_DB[0]

SQLITE_DATABASE_PATH = 'data/securities.db'
SQLITE_URI = f'sqlite:///{SQLITE_DATABASE_PATH}'
POSTGRES_URI = f'postgresql+psycopg2://{dbuser}:{dbpw}@localhost:{port}/{db}'

if ACTIVE_DB == OPTIONS_DB[0]:
    ACTIVE_URI = POSTGRES_URI
elif ACTIVE_DB == OPTIONS_DB[1]:
    ACTIVE_URI = SQLITE_URI

VALID_SPREADSHEETS = ('google', 'excel')
GOOGLE_SHEETNAME_EXCHANGES = 'Exchanges'
GOOGLE_SHEETNAME_INDEXES = 'Indexes'
EXCEL_SHEETNAME_EXCHANGES = 'data/symbols/exchanges.xlsx'
EXCEL_SHEETNAME_INDEXES = 'data/symbols/indexes.xlsx'

EXCHANGES = ({'abbreviation':'NASDAQ', 'name':'National Association of Securities Dealers Automated Quotations'},
             {'abbreviation':'NYSE',   'name':'New York Stock Exchange'},
             {'abbreviation':'AMEX',   'name':'American Stock Exchange'})

INDEXES =   ({'abbreviation':'SP500',  'name':'Standard & Poors 500'},
             {'abbreviation':'DOW',    'name':'DOW industrials'},
             {'abbreviation':'CUSTOM', 'name':'Custom Index'})