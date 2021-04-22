import os, time
from urllib.error import HTTPError

from sqlalchemy import create_engine, inspect, and_, or_
from sqlalchemy.orm import sessionmaker

import data as d
from data import store as s
from data import models as m
from fetcher import fetcher as f
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

    def delete_database(self, recreate=True):
        if d.ACTIVE_DB == d.OPTIONS_DB[1]:
            if os.path.exists(d.SQLITE_DATABASE_PATH):
                os.remove(d.SQLITE_DATABASE_PATH)
                logger.info(f'{__name__}: Deleted {d.SQLITE_DATABASE_PATH}')
            else:
                logger.warning(f'{__name__}: File does not exist: {d.SQLITE_DATABASE_PATH}')
        else:
            m.Base.metadata.drop_all(self.engine)

        if recreate:
            self.create_database()

    def create_exchanges(self):
        with self.session() as session, session.begin():
            for exchange in d.EXCHANGES:
                exc = m.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
                session.add(exc)
                logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

    def populate_exchange(self, exchange):
        self.error = ''
        self.invalid_symbols = []
        self.retry = 0

        with self.session() as session:
            e = session.query(m.Exchange.abbreviation).filter(m.Exchange.abbreviation==exchange).one()
            abrev = e.abbreviation

        symbols = s.get_exchange_symbols_master(abrev)
        if len(symbols) > 0:
            self._add_securities_to_exchange_th(symbols, abrev)
        else:
            logger.warning(f'{__name__}: No symbols for {exchange}')

    def refresh_exchange(self, exchange, area):
        self.error = ''
        self.invalid_symbols = []
        self.retry = 0
        self.items_completed = 0

        with self.session() as session:
            # Throws exception if does not exist
            session.query(m.Exchange.abbreviation).filter(m.Exchange.abbreviation==exchange).one()

        if area == 'securities':
            missing = self.identify_missing_securities(exchange)
            self.items_total = len(missing)
            self.error = 'None'
            if self.items_total > 0:
                self._add_securities_to_exchange_th(missing, exchange)
        elif area == 'companies':
            self.error = 'None'
            missing = self._identify_incomplete_securities_companies_th(exchange)
            self.items_total = len(missing)
            self.error = 'Done'
        elif area == 'prices':
            self.error = 'None'
            missing = self._identify_incomplete_securities_price_th(exchange)
            self.items_total = len(missing)
            self.error = 'Done'

    def delete_exchange(self, exchange):
        with self.session() as session, session.begin():
            exc = session.query(m.Exchange.abbreviation).filter(m.Exchange.abbreviation==exchange)
            if exc is not None:
                exc.delete(synchronize_session=False)

    def create_indexes(self):
        with self.session() as session, session.begin():
            for index in d.INDEXES:
                ind = m.Index(abbreviation=index['abbreviation'], name=index['name'])
                session.add(ind)
                logger.info(f'{__name__}: Added index {index["abbreviation"]}')

    def populate_index(self, index):
        self.error = ''
        valid = []

        with self.session() as session:
            i = session.query(m.Index.abbreviation).filter(m.Index.abbreviation==index).one()
            symbols = s.get_index_symbols_master(i.abbreviation)
            for symbol in symbols:
                ticker = session.query(m.Security.ticker).filter(m.Security.ticker==symbol).one_or_none()
                if ticker is not None:
                    valid += [ticker.ticker]

        if len(valid) > 0:
            self._add_securities_to_index_th(valid, i.abbreviation)
            logger.info(f'{__name__}: Populated index {index}')
        else:
            self.error = 'No symbols'
            logger.warning(f'{__name__}: No symbols found for {index}')

    def delete_index(self, index):
        with self.session() as session, session.begin():
            ind = session.query(m.Index.abbreviation).filter(m.Index.abbreviation==index)
            if ind is not None:
                ind.delete(synchronize_session=False)
                logger.info(f'{__name__}: Deleted index {index}')
            else:
                logger.error(f'{__name__}: Index {index} does not exist')

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

    def get_exchange_info(self):
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if len(tables) > 0:
            with self.session() as session:
                exchanges = session.query(m.Exchange).all()
                for e in exchanges:
                    s = session.query(m.Security).filter(m.Security.exchange_id == e.id)
                    if s is not None:
                        info += [{'exchange':e.abbreviation, 'count':s.count()}]

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
        if s.is_exchange(list):
            symbols = self.get_exchange_symbols_master(list)
        elif s.is_index(list):
            symbols = s.get_index_symbols_master(list)

        if len(symbols) > 0:
            for s in symbols:
                if not f.validate_ticker(s, force=True):
                    invalid += [s]

        return invalid

    def identify_missing_securities(self, exchange):
        missing = []
        tickers = s.get_exchange_symbols_master(exchange)
        logger.info(f'{__name__}: {len(tickers)} total symbols in {exchange}')
        with self.session() as session:
            exc = session.query(m.Exchange.id, m.Exchange.abbreviation).filter(m.Exchange.abbreviation==exchange).one()
            for sec in tickers:
                t = session.query(m.Security.ticker, m.Security.exchange_id).filter(and_(m.Security.ticker==sec, m.Security.exchange_id==exc.id)).one_or_none()
                if t is None:
                    missing += [sec]

        logger.info(f'{__name__}: {len(missing)} missing symbols in {exchange}')
        return missing

    def identify_common_securities(self):
        nasdaq = s.get_exchange_symbols_master('NASDAQ')
        nyse = s.get_exchange_symbols_master('NYSE')
        amex = s.get_exchange_symbols_master('AMEX')

        nasdaq_nyse = nasdaq.intersection(nyse)
        nasdaq_amex = nasdaq.intersection(amex)
        nyse_amex = nyse.intersection(amex)

        return nasdaq_nyse, nasdaq_amex, nyse_amex

    def _add_securities_to_exchange_th(self, tickers, exchange):
        self.items_total = len(tickers)
        self.items_completed = 0

        with self.session() as session:
            exc = session.query(m.Exchange).filter(m.Exchange.abbreviation==exchange).one()
            self.items_total = len(tickers)
            self.error = 'None'

            for sec in tickers:
                s = session.query(m.Security).filter(m.Security.ticker==sec).one_or_none()
                if s is None:
                    exc.securities += [m.Security(sec)]
                    session.commit()

                    try:
                        self._add_company_to_security(sec)
                        self._add_pricing_to_security(sec)
                    except (ValueError, KeyError, IndexError) as e:
                        self.invalid_symbols += [sec]
                        logger.warning(f'{__name__}: Company info invalid: {sec}, {str(e)}')
                    except HTTPError as e:
                        self.invalid_symbols += [sec]
                        self.retry += 1
                        logger.warning(f'{__name__}: HTTP Error. Retrying... {self.retry}, {str(e)}')
                        if self.retry > 10:
                            self.error = 'HTTP Error'
                            logger.error(f'{__name__}: HTTP Error. Too many retries. {str(e)}')
                        else:
                            time.sleep(5.0)
                    except RuntimeError as e:
                        self.error = 'Runtime Error'
                        logger.error(f'{__name__}: Runtime Error, {str(e)}')
                    else:
                        self.retry = 0
                        logger.info(f'{__name__}: Added {sec} to exchange {exchange}')
                else:
                    logger.info(f'{__name__}: {sec} already exists')

                self.items_completed += 1

                if self.error != 'None':
                    logger.warning(f'{__name__}: Cancelling operation')
                    break

    def _add_securities_to_index_th(self, tickers, index):
        self.items_total = 0
        self.items_completed = 0

        with self.session() as session, session.begin():
            ind = session.query(m.Index).filter(m.Index.abbreviation==index).one()
            self.items_total = len(tickers)
            self.error = 'None'
            for t in tickers:
                if self.error != 'None':
                    break

                s = session.query(m.Security).filter(m.Security.ticker==t).one_or_none()
                if s.index1_id is None:
                    s.index1_id = ind.id
                elif s.index2_id is None:
                    s.index2_id = ind.id

                self.items_completed += 1

                logger.info(f'{__name__}: Added {t} to index {index}')

    def _identify_incomplete_securities_companies_th(self, exchange):
        missing = []
        with self.session() as session:
            exc = session.query(m.Exchange.id).filter(m.Exchange.abbreviation==exchange).one()
            sec = session.query(m.Security.ticker, m.Security.id).filter(m.Security.exchange_id==exc.id).all()
            for t in sec:
                c = session.query(m.Company.id).filter(m.Company.security_id==t.id).limit(1)
                if c.first() is None:
                    logger.info(f'{__name__}: {t.ticker} incomplete company info')
                    missing += [t.ticker]

        logger.info(f'{__name__}: {len(missing)} incomplete symbol company info')
        return missing

    def _identify_incomplete_securities_price_th(self, exchange):
        missing = []
        with self.session() as session:
            exc = session.query(m.Exchange.id).filter(m.Exchange.abbreviation==exchange).one()
            sec = session.query(m.Security.ticker, m.Security.id).filter(m.Security.exchange_id==exc.id).all()
            for t in sec:
                c = session.query(m.Price.id).filter(m.Price.security_id==t.id).limit(1)
                if c.first() is None:
                    logger.info(f'{__name__}: {t.ticker} incomplete price info')
                    missing += [t.ticker]

        logger.info(f'{__name__}: {len(missing)} incomplete symbol price info')
        return missing

    def _add_company_to_security(self, ticker):
        with self.session() as session, session.begin():
            s = session.query(m.Security).filter(m.Security.ticker==ticker).one_or_none()
            company = f.get_company(ticker)
            if company is None:
                logger.info(f'{__name__}: No company for {ticker}')
            elif company.info is None:
                logger.info(f'{__name__}: No company information for {ticker}')
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
            s = session.query(m.Security).filter(m.Security.ticker==ticker).one_or_none()
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


if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    manager = Manager()
    # missing = manager.identify_incomplete_securities_companies('NYSE')
    missing = manager._identify_incomplete_securities_price_th('AMEX')
    print(len(missing))

    # invalid = manager.validate_list('NASDAQ')
    # print (invalid)

    # manager.delete_database(recreate=True)
    # manager.build_exchanges()
    # manager.build_indexes()
    # manager.populate_exchange('AMEX')
    # manager.populate_index('SP500')
    # manager.populate_index('DOW')
