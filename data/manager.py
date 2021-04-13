import os
from urllib.error import HTTPError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fetcher.google import Google
from fetcher.excel import Excel

import data as d
from fetcher import fetcher as f
from utils import utils as u
from data import models as m

logger = u.get_logger()

class Manager:
    def __init__(self):
        self.engine = create_engine(f'sqlite:///{d.SQLITE_DATABASE_PATH}', echo=False)
        self.session = sessionmaker(bind=self.engine)
        self.items_total = 0
        self.items_completed = 0
        self.exchange = ''
        self.invalid_symbols = []
        self.error = ''

    def build_exchanges(self):
        with self.session.begin() as session:
            for exchange in d.EXCHANGES:
                exc = m.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
                session.add(exc)
                logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

    def build_indexes(self):
        with self.session.begin() as session:
            for index in d.INDEXES:
                exc = m.Index(abbreviation=index['abbreviation'], name=index['name'])
                session.add(exc)
                logger.info(f'{__name__}: Added index {index["abbreviation"]}')

    def populate_exchange(self, exchange):
        self.error = ''
        self.invalid_symbols = []

        with self.session.begin() as session:
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).first()
            if exc is not None:
                symbols = self.get_exchange_symbols(exc.abbreviation)
                self.add_securities_to_exchange(symbols, exc.abbreviation)
            else:
                raise ValueError(f'Unknown exchange {exchange}')

    def populate_index(self, index):
        self.error = ''
        valid = []

        with self.session() as session:
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
                    self.error = 'No symbols'
            else:
                raise ValueError(f'Unknown index {index}')

    def add_securities_to_exchange(self, tickers, exchange):
        self.items_total = 0
        self.items_completed = 0

        with self.session() as session, session.begin():
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation == exchange).first()
            if exc is not None:
                self.items_total = len(tickers)
                self.error = 'None'
                for sec in tickers:
                    exists = session.query(m.Security).filter(m.Security.ticker==sec.upper()).first()
                    if exists is None:
                        s = m.Security(sec)
                        exc.securities += [s]
                        session.commit()

                        self.add_company_to_security(sec)
                        self.add_pricing_to_security(sec)

                        logger.info(f'{__name__}: Added {sec} to exchange {exchange}')
                    else:
                        logger.info(f'{__name__}: {sec} already exists')

                    self.items_completed += 1
            else:
                raise ValueError(f'Unknown exchange {exchange}')

    def add_securities_to_index(self, tickers, index):
        self.items_total = 0
        self.items_completed = 0

        with self.session() as session, session.begin():
            ind = session.query(m.Index).filter(m.Index.abbreviation == index).first()
            if ind is not None:
                self.items_total = len(tickers)
                self.error = 'None'
                for t in tickers:
                    s = session.query(m.Security).filter(m.Security.ticker == t).first()
                    if s.index1_id is None:
                        s.index1_id = ind.id
                    elif s.index2_id is None:
                        s.index2_id = ind.id
                    session.commit()

                    self.items_completed += 1

                    logger.info(f'{__name__}: Added {t} to index {index}')
            else:
                session.close()
                raise ValueError(f'Unknown index {index}')

        session.close()

    def add_company_to_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
            if s is not None:
                try: # YFinance & Pandas throw a lot of exceptions for sketchy data and connection issues
                    company = f.get_company(ticker)
                    if company is not None:
                        if company.info is not None:
                            c = m.Company()
                            c.name = company.info['shortName'] if company.info['shortName'] else '<invalid>'
                            c.description = company.info['longBusinessSummary']
                            c.url = company.info['website']
                            c.sector = company.info['sector']
                            c.industry = company.info['industry']

                            s.company = [c]

                            logger.info(f'{__name__}: Added company information for {ticker}')
                except (ValueError, KeyError, IndexError) as e:
                    self.invalid_symbols += [ticker]
                    logger.info(f'{__name__}: Company info invalid: {ticker}: {str(e)}')
                except HTTPError as e:
                    self.error = 'HTTP Error'
                    logger.info(f'{__name__}: HTTP Error {str(e)}')
            else:
                raise ValueError(f'Unknown ticker {ticker}')

        session.close()

    def add_pricing_to_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
            if s is not None:
                try: # YFinance & Pandas throw a lot of exceptions for sketchy data and connection issues
                    history = f.get_history(ticker, -1)
                    if history is not None:
                        history.reset_index(inplace=True)
                        for index, price in history.iterrows():
                            p = m.Price()
                            p.date = price['Date']
                            p.open = price['Open']
                            p.high = price['High']
                            p.low = price['Low']
                            p.close = price['Close']
                            p.volume = price['Volume']
                            s.pricing += [p]

                        logger.info(f'{__name__}: Added pricing to {ticker}')
                except (ValueError, KeyError, IndexError) as e:
                    self.invalid_symbols += [ticker]
                    logger.info(f'{__name__}: Pricing info invalid: {ticker}: {str(e)}')
                except HTTPError as e:
                    self.error = 'HTTP Error'
                    logger.info(f'{__name__}: HTTP Error {str(e)}')
            else:
                raise ValueError(f'Unknown ticker {ticker}')

        session.close()

    def get_exchange_symbols(self, exchange, type='google'):
        table = None
        symbols = []

        if self.is_exchange(exchange):
            if type == 'google':
                table = Google(d.GOOGLE_SHEETNAME_EXCHANGES)
            elif type == 'excel':
                table = Excel(d.EXCEL_SHEETNAME_EXCHANGES)
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

        if self.is_index(index):
            if type == 'google':
                table = Google(d.GOOGLE_SHEETNAME_INDEXES)
            elif type == 'excel':
                table = Excel(d.EXCEL_SHEETNAME_INDEXES)
            else:
                raise ValueError(f'Invalid spreadsheet type: {type}')

            if table.open(index):
                symbols = table.get_column(1)
            else:
                logger.warning(f'{__name__}: Unable to open exchange spreadsheet {index}')
        else:
            raise ValueError(f'Invalid index name: {index}')

        return symbols

    def delete_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
            if s is not None:
                session.delete(s)

    def get_database_info(self):
        info = []

        with self.session() as session:
            tables = m.Base.metadata.tables
            for table in tables:
                count = session.query(tables[table]).count()
                info += [{'table':table, 'count':count}]

        return info

    def get_exchange_info(self, exchange=''):
        info = []

        with self.session() as session:
            if not exchange:
                exchanges = session.query(m.Exchange)
                for e in exchanges:
                    s = session.query(m.Security).filter(m.Security.exchange_id == e.id)
                    info += [{'exchange':e.abbreviation, 'count':s.count()}]
            else:
                e = session.query(m.Exchange).filter(m.Exchange.abbreviation == exchange).first()
                s = session.query(m.Security).filter(m.Security.exchange_id == e.id)
                info = [{'exchange':e.abbreviation, 'count':s.count()}]

        return info

    def delete_database(self, recreate=False):
        if os.path.exists(d.SQLITE_DATABASE_PATH):
            os.remove(d.SQLITE_DATABASE_PATH)
        else:
            logger.info(f'{__name__}: File does not exist: {d.SQLITE_DATABASE_PATH}')

        if recreate:
            m.Base.metadata.create_all(self.engine)

    def validate_list(self, list):
        symbols = []
        invalid = []
        if self.is_exchange(list):
            symbols = self.get_exchange_symbols(list)
        elif self.is_index(list):
            symbols = self.get_index_symbols(list)

        if len(symbols) > 0:
            for s in symbols:
                if not f.validate_ticker(s, force=True):
                    invalid += [s]

        return invalid

    @staticmethod
    def is_exchange(exchange):
        ret = False
        for e in d.EXCHANGES:
            if exchange == e['abbreviation']:
                ret = True
                break
        return ret

    @staticmethod
    def is_index(index):
        ret = False
        for i in d.INDEXES:
            if index == i['abbreviation']:
                ret = True
                break
        return ret

if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    manager = Manager()
    print(manager.get_exchange_info('AMEX'))

    # invalid = manager.validate_list('NASDAQ')
    # print (invalid)

    # manager.delete_database(recreate=True)
    # manager.build_exchanges()
    # manager.build_indexes()
    # manager.populate_exchange('AMEX')
    # manager.populate_index('SP500')
    # manager.populate_index('DOW')
