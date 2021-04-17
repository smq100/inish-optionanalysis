import os, time
from urllib.error import HTTPError

from sqlalchemy import create_engine, inspect, and_, or_
from sqlalchemy.orm import sessionmaker

import data as d
from data import store as o
from data import models as m
from fetcher import fetcher as f
from fetcher.google import Google
from fetcher.excel import Excel
from utils import utils as u

logger = u.get_logger()

class Manager:
    def __init__(self):
        self.engine = create_engine(d.ACTIVE_URI, echo=False)
        self.session = sessionmaker(bind=self.engine)
        self.exchange = ''
        self.items_total = 0
        self.items_completed = 0
        self.invalid_symbols = []
        self.error = ''
        self.retry = 0

    def create_database(self):
        m.Base.metadata.create_all(self.engine)

    def delete_database(self, recreate=False):
        if d.ACTIVE_DB == 'sqlite':
            if os.path.exists(d.SQLITE_DATABASE_PATH):
                os.remove(d.SQLITE_DATABASE_PATH)
            else:
                logger.warning(f'{__name__}: File does not exist: {d.SQLITE_DATABASE_PATH}')
        else:
            m.Base.metadata.drop_all(self.engine)

        if recreate:
            self.create_database()

    def build_exchanges(self):
        with self.session() as session, session.begin():
            for exchange in d.EXCHANGES:
                exc = m.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
                session.add(exc)
                logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

    def build_indexes(self):
        with self.session() as session, session.begin():
            for index in d.INDEXES:
                ind = m.Index(abbreviation=index['abbreviation'], name=index['name'])
                session.add(ind)
                logger.info(f'{__name__}: Added index {index["abbreviation"]}')

    def populate_exchange(self, exchange):
        self.error = ''
        self.invalid_symbols = []
        self.retry = 0

        exc = None
        with self.session() as session:
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).first()
            abrev = exc.abbreviation

        if exc is not None:
            symbols = self._get_exchange_symbols(abrev)
            self._add_securities_to_exchange(symbols, abrev)
        else:
            self.error = f'Unknown exchange {exchange}'
            logger.warning(f'{__name__}: Exchange not found: {exchange}')

    def populate_index(self, index):
        self.error = ''
        valid = []

        with self.session() as session:
            i = session.query(m.Index).filter(m.Index.abbreviation==index).first()
            if i is not None:
                symbols = self._get_index_symbols(i.abbreviation)
                for symbol in symbols:
                    ticker = session.query(m.Security).filter(m.Security.ticker==symbol).first()
                    if ticker is not None:
                        valid += [ticker.ticker]
            else:
                self.error = 'Unknown index'
                logger.warning(f'{__name__}: Index not found: {index}')

        if len(valid) > 0:
            self._add_securities_to_index(valid, i.abbreviation)
        else:
            self.error = 'No symbols'
            logger.warning(f'{__name__}: No symbols found for {index}')

    def delete_exchange(self, exchange):
        with self.session() as session, session.begin():
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).first()
            if exc is not None:
                sec = session.query(m.Security).filter(m.Security.exchange_id==exc.id)
                if sec is not None:
                    sec.delete(synchronize_session=False)

    def get_database_info(self):
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
            with self.session() as session:
                tables = m.Base.metadata.tables
                for table in tables:
                    count = session.query(tables[table]).count()
                    info += [{'table':table, 'count':count}]
        else:
            u.print_error('No tables in database')
            logger.warning('{__name__}: No tables in database')

        return info

    def get_exchange_info(self, exchange=''):
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
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

    def get_index_info(self, index=''):
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
            with self.session() as session:
                if not index:
                    indexes = session.query(m.Index)
                    for i in indexes:
                        s = session.query(m.Security).filter(or_(m.Security.index1_id == i.id, m.Security.index2_id == i.id))
                        info += [{'index':i.abbreviation, 'count':s.count()}]
                else:
                    i = session.query(m.Index).filter(m.Index.abbreviation == index).first()
                    s = session.query(m.Security).filter(or_(m.Security.index1_id == i.id, m.Security.index2_id == i.id))
                    info = [{'index':i.abbreviation, 'count':s.count()}]

        return info

    def validate_list(self, list):
        symbols = []
        invalid = []
        if o.is_exchange(list):
            symbols = self._get_exchange_symbols(list)
        elif o.is_index(list):
            symbols = self._get_index_symbols(list)

        if len(symbols) > 0:
            for s in symbols:
                if not f.validate_ticker(s, force=True):
                    invalid += [s]

        return invalid

    def _add_securities_to_exchange(self, tickers, exchange):
        self.items_total = 0
        self.items_completed = 0

        with self.session() as session:
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).first()
            if exc is not None:
                self.items_total = len(tickers)
                self.error = 'None'
                for sec in tickers:
                    exists = session.query(m.Security).filter(m.Security.ticker==sec.upper()).first()
                    if exists is None:
                        s = m.Security(sec)
                        exc.securities += [s]
                        session.commit()

                        try:
                            self._add_company_to_security(sec)
                            self._add_pricing_to_security(sec)
                        except (ValueError, KeyError, IndexError) as e:
                            self.invalid_symbols += [sec]
                            logger.warning(f'{__name__}: Company info invalid: {sec}: {str(e)}')
                        except HTTPError as e:
                            self.retry += 1
                            logger.warning(f'{__name__}: HTTP Error. Retrying - {self.retry}, {str(e)}')
                            if self.retry > 10:
                                self.error = 'HTTP Error'
                                logger.error(f'{__name__}: HTTP Error. Too many retries. {str(e)}')
                            else:
                                time.sleep(5.0)
                        except RuntimeError as e:
                            self.error = 'Runtime Error'
                            logger.error(f'{__name__}: Runtime Error, Yahoo Finance down? {str(e)}')
                        else:
                            self.retry = 0

                        logger.info(f'{__name__}: Added {sec} to exchange {exchange}')
                    else:
                        logger.info(f'{__name__}: {sec} already exists')

                    self.items_completed += 1

                    if self.error != 'None':
                        logger.warning(f'{__name__}: Cancelling operation')
                        break

    def _add_securities_to_index(self, tickers, index):
        self.items_total = 0
        self.items_completed = 0

        with self.session() as session, session.begin():
            ind = session.query(m.Index).filter(m.Index.abbreviation==index).first()
            if ind is not None:
                self.items_total = len(tickers)
                self.error = 'None'
                for t in tickers:
                    if self.error != 'None':
                        break

                    s = session.query(m.Security).filter(m.Security.ticker == t).first()
                    if s.index1_id is None:
                        s.index1_id = ind.id
                    elif s.index2_id is None:
                        s.index2_id = ind.id

                    self.items_completed += 1

                    logger.info(f'{__name__}: Added {t} to index {index}')

    def _add_company_to_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker == ticker).first()
            if s is not None:
                company = f.get_company(ticker)
                if company is None:
                    pass
                elif company.info is None:
                    pass
                else:
                    c = m.Company()
                    c.name = company.info['shortName'] if company.info['shortName'] else '<error>'
                    c.description = company.info['longBusinessSummary'][:4999]
                    c.url = company.info['website']
                    c.sector = company.info['sector']
                    c.industry = company.info['industry']
                    s.company = [c]

                    logger.info(f'{__name__}: Added company information for {ticker}')

    def _add_pricing_to_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker==ticker).first()
            if s is not None:
                history = f.get_history(ticker)
                if history is not None:
                    history.reset_index(inplace=True)
                    for index, price in history.iterrows():
                        if price['Date']:
                            p = m.Price()
                            p.date = price['Date']
                            p.open = price['Open']
                            p.high = price['High']
                            p.low = price['Low']
                            p.close = price['Close']
                            p.volume = price['Volume']
                            s.pricing += [p]

                    logger.info(f'{__name__}: Added pricing to {ticker}')
            else:
                raise ValueError(f'Unknown ticker {ticker}')

    @staticmethod
    def _get_exchange_symbols(exchange, type='google'):
        table = None
        symbols = []

        if o.is_exchange(exchange):
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

    @staticmethod
    def _get_index_symbols(index, type='google'):
        table = None
        symbols = []

        if o.is_index(index):
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
