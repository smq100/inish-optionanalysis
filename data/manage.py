import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fetcher.google import Google
from fetcher.excel import Excel

from fetcher import fetcher as f
from utils import utils as u
from . import models as m

logger = u.get_logger()

SQLITE_DATABASE_PATH = 'data/test.db'
GOOGLE_SHEETNAME_EXCHANGES = 'Exchanges'
GOOGLE_SHEETNAME_INDEXES = 'Indexes'
EXCEL_SHEETNAME_EXCHANGES = 'data/symbols/exchanges.xlsx'
EXCEL_SHEETNAME_INDEXES = 'data/symbols/indexes.xlsx'

class Manager:
    def __init__(self):
        self.engine = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}')#, echo=True)

    def build_exchanges(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        for exchange in m.EXCHANGES:
            exc = m.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
            session.add(exc)
            logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

        session.commit()
        session.close()

    def build_indexes(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        for index in m.INDEXES:
            exc = m.Index(abbreviation=index['abbreviation'], name=index['name'])
            session.add(exc)
            logger.info(f'{__name__}: Added index {index["abbreviation"]}')

        session.commit()
        session.close()

    def populate_exchange(self, exchange):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        e = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).first()
        if e is not None:
            symbols = self.get_exchange_symbols(e.abbreviation)
            self.add_securities_to_exchange(symbols[:5], e.abbreviation)
        else:
            session.close()
            raise ValueError(f'Unknown exchange {exchange}')

        session.close()

    def populate_index(self, index):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        valid = []
        i = session.query(m.Index).filter(m.Index.abbreviation==index).first()
        if i is not None:
            symbols = self.get_index_symbols(i.abbreviation)
            for s in symbols:
                t = session.query(m.Security).filter(m.Security.ticker==s).first()
                if t is not None:
                    valid += [t.ticker]

            if len(valid) > 0:
                self.add_securities_to_index(valid, i.abbreviation)
        else:
            session.close()
            raise ValueError(f'Unknown index {index}')

        session.close()

    def add_securities_to_exchange(self, tickers, exchange):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        exc = session.query(m.Exchange).filter(m.Exchange.abbreviation == exchange).first()
        if exc is not None:
            for sec in tickers:
                s = m.Security(sec)
                exc.securities += [s]
                session.commit()

                self.add_company_to_security(sec)
                self.add_pricing_to_security(sec)
                session.commit()

                logger.info(f'{__name__}: Added security {sec} to exchange {exchange}')
        else:
            session.close()
            raise ValueError(f'Unknown exchange {exchange}')

        session.close()

    def add_securities_to_index(self, tickers, index):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        ind = session.query(m.Index).filter(m.Index.abbreviation == index).first()
        if ind is not None:
            for t in tickers:
                s = session.query(m.Security).filter(m.Security.ticker == t).first()
                s.index_id = ind.id
                session.commit()

                logger.info(f'{__name__}: Added security {t} to index {index}')
        else:
            session.close()
            raise ValueError(f'Unknown index {index}')

        session.close()

    def add_company_to_security(self, ticker):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
        if s is not None:
            try: # YFinance & Pandas throw a lot of exceptions for sketchy data
                company = f.get_company(ticker)
                if company is not None:
                    if company.info is not None:
                        c = m.Company()
                        c.name = company.info['shortName']
                        c.description = company.info['longBusinessSummary']
                        c.url = company.info['website']
                        c.sector = company.info['sector']
                        c.industry = company.info['industry']

                        s.company = [c]
                        session.commit()

                        logger.info(f'{__name__}: Added company {c.name} to {ticker}')
            except (ValueError, KeyError) as e:
                logger.warning(f'{__name__}: Company info invalid: {ticker}: {str(e)}')
                session.close()
        else:
            session.close()
            raise ValueError(f'Unknown ticker {ticker}')

        session.close()

    def add_pricing_to_security(self, ticker):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
        if s is not None:
            try: # YFinance & Pandas throw a lot of exceptions for sketchy data
                history = f.get_history(ticker, -1)
                if history is not None:
                    for date in history:
                        print(history['Date'])
                    # p = m.Price()

                    logger.info(f'{__name__}: Added pricing to {ticker}')
            except (ValueError, KeyError) as e:
                logger.warning(f'{__name__}: Company info invalid: {ticker}: {str(e)}')
                session.close()
        else:
            session.close()
            raise ValueError(f'Unknown ticker {ticker}')

        session.close()

    def get_exchange_symbols(self, exchange, type='google'):
        table = None
        symbols = []

        if self._is_valid_exchange(exchange):
            if type == 'google':
                table = Google(GOOGLE_SHEETNAME_EXCHANGES)
            elif type == 'excel':
                table = Excel(EXCEL_SHEETNAME_EXCHANGES)
            else:
                raise ValueError(f'Invalid table type: {type}')

            if table.open(exchange):
                symbols = table.get_column(1)
            else:
                logger.warning(f'{__name__}: Unable to open index spreadsheet {exchange}')
        else:
            raise ValueError(f'Invalid exchange name: {exchange}')

        return symbols

    def get_index_symbols(self, index, type='google'):
        table = None
        symbols = []

        if self._is_valid_index(index):
            if type == 'google':
                table = Google(GOOGLE_SHEETNAME_INDEXES)
            elif type == 'excel':
                table = Excel(EXCEL_SHEETNAME_INDEXES)
            else:
                raise ValueError(f'Invalid table type: {type}')

            if table.open(index):
                symbols = table.get_column(1)
            else:
                logger.warning(f'{__name__}: Unable to open exchange spreadsheet {index}')
        else:
            raise ValueError(f'Invalid index name: {index}')

        return symbols

    def delete_security(self, ticker):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
        if s is not None:
            session.delete(s)
            session.commit()

        session.close()

    def delete_database(self):
        if os.path.exists(SQLITE_DATABASE_PATH):
            os.remove(SQLITE_DATABASE_PATH)
        else:
            logger.error(f'{__name__}: File does not exist: {SQLITE_DATABASE_PATH}')

    def print_securities(self, exchange):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        e = session.query(m.Exchange).filter(m.Exchange.abbreviation == exchange).first()
        if e is not None:
            for s in e.securities:
                print(s)

        session.close()

    @staticmethod
    def _is_valid_exchange(exchange):
        ret = False
        for e in m.EXCHANGES:
            if exchange == e['abbreviation']:
                ret = True
                break
        return ret

    @staticmethod
    def _is_valid_index(index):
        ret = False
        for i in m.INDEXES:
            if index == i['abbreviation']:
                ret = True
                break
        return ret

if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    f.initialize()

    manager = Manager()
    manager.delete_database()
    m.Base.metadata.create_all(manager.engine)
    manager.build_exchanges()
    manager.build_indexes()
    manager.populate_exchange('TEST')
    manager.populate_index('TEST')
