import os, time, json
from datetime import date
from concurrent import futures
from urllib.error import HTTPError

from sqlalchemy import create_engine, inspect, and_, or_
from sqlalchemy.orm import sessionmaker
import numpy as np

from base import Threaded
import data as d
from data import store as store
from data import models as models
from fetcher import fetcher as fetcher
from utils import utils as utils

logger = utils.get_logger()

LOG_DIR = './log'

class Manager(Threaded):
    def __init__(self):
        super().__init__()

        self.engine = create_engine(d.ACTIVE_URI, echo=False)
        self.session = sessionmaker(bind=self.engine)
        self.exchange = ''
        self.invalid_symbols = []
        self.retry = 0
        self._concurrency = 3 if d.ACTIVE_DB == 'SQLite' else 6

    def create_database(self):
        models.Base.metadata.create_all(self.engine)

    def delete_database(self, recreate=True):
        if d.ACTIVE_DB == d.OPTIONS_DB[1]:
            if os.path.exists(d.SQLITE_DATABASE_PATH):
                os.remove(d.SQLITE_DATABASE_PATH)
                logger.info(f'{__name__}: Deleted {d.SQLITE_DATABASE_PATH}')
            else:
                logger.warning(f'{__name__}: File does not exist: {d.SQLITE_DATABASE_PATH}')
        else:
            models.Base.metadata.drop_all(self.engine)

        if recreate:
            self.create_database()

    def create_exchanges(self):
        with self.session.begin() as session:
            for exchange in d.EXCHANGES:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation==exchange['abbreviation']).one_or_none()
                if e is None:
                    exc = models.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
                    session.add(exc)
                    logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

    @Threaded.threaded
    def populate_exchange(self, exchange):
        self.invalid_symbols = []
        self.retry = 0
        abbrev = ''

        with self.session() as session:
            e = session.query(models.Exchange.abbreviation).filter(models.Exchange.abbreviation==exchange).one()
            abbrev = e.abbreviation

        tickers = store.get_exchange_symbols_master(abbrev)

        if len(tickers) > 10:
            self.task_total = len(tickers)
            self.task_error = 'None'

            # Split the list and remove any empty lists
            lists = np.array_split(tickers, self._concurrency)
            lists = [i for i in lists if i is not None]

            with futures.ThreadPoolExecutor() as executor:
                self.task_futures = executor.map(self._add_securities_to_exchange, lists, [abbrev]*len(lists))

            for future in self.task_futures:
                if future is None:
                    self.task_results += ['Ok']
                else:
                    self.task_results += [future.result()]

        else:
            logger.warning(f'{__name__}: No symbols for {exchange}')

        self.task_error = 'Done'

    @Threaded.threaded
    def refresh_exchange(self, exchange, area):
        self.invalid_symbols = []
        self.retry = 0

        with self.session() as session:
            # Throws exception if does not exist
            session.query(models.Exchange.abbreviation).filter(models.Exchange.abbreviation==exchange).one()

        if area == 'companies':
            self.task_error = 'None'
            missing = self.identify_incomplete_securities_companies(exchange, live=True, log=True)
            self.task_total = len(missing)

            # Split the list and remove any empty lists
            lists = np.array_split(missing, self._concurrency)
            lists = [i for i in lists if i is not None]

            def _companies(tickers):
                for ticker in tickers:
                    self.task_symbol = ticker
                    if self._add_company_to_security(ticker):
                        self.task_success += 1
                    self.task_completed += 1

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                for list in lists:
                    self.task_futures += [executor.submit(_companies, list)]

            self.task_error = 'Done'
        elif area == 'pricing':
            self.task_error = 'None'
            missing = self.identify_incomplete_securities_price(exchange, live=True, log=True)
            self.task_total = len(missing)

            # Split the list and remove any empty lists
            lists = np.array_split(missing, self._concurrency)
            lists = [i for i in lists if i is not None]

            def _pricing(tickers):
                for ticker in tickers:
                    self.task_symbol = ticker
                    if self._add_pricing_to_security(ticker):
                        self.task_success += 1
                    self.task_completed += 1

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                for list in lists:
                    self.task_futures += [executor.submit(_pricing, list)]

            self.task_error = 'Done'
        else:
            self.task_error = 'Invalid area'
            raise ValueError(f'{self.task_error}: {area}')

    @Threaded.threaded
    def delete_exchange(self, exchange):
        self.task_error = 'None'
        with self.session.begin() as session:
            exc = session.query(models.Exchange).filter(models.Exchange.abbreviation==exchange)
            if exc is not None:
                exc.delete(synchronize_session=False)
        self.task_error = 'Done'

    def create_indexes(self):
        with self.session.begin() as session:
            for index in d.INDEXES:
                i = session.query(models.Index.id).filter(models.Index.abbreviation==index['abbreviation']).one_or_none()
                if i is None:
                    ind = models.Index(abbreviation=index['abbreviation'], name=index['name'])
                    session.add(ind)
                    logger.info(f'{__name__}: Added index {index["abbreviation"]}')

    @Threaded.threaded
    def update_pricing(self, exchange=''):
        tickers = store.get_symbols(exchange)
        self.task_total = len(tickers)

        # Split the list and remove any empty lists
        lists = np.array_split(tickers, self._concurrency)
        lists = [i for i in lists if i is not None]

        def _pricing(tickers):
            with self.session() as session:
                for sec in tickers:
                    self.task_symbol = sec
                    days = self._refresh_pricing(sec, session)
                    session.commit()

                    if days > 0:
                        self.task_success += 1

                    self.task_completed += 1

        self.task_error = 'None'

        with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            for list in lists:
                self.task_futures += [executor.submit(_pricing, list)]

        self.task_error = 'Done'

    @Threaded.threaded
    def populate_index(self, index):
        valid = []

        with self.session.begin() as session:
            self.task_error = 'None'
            try:
                i = session.query(models.Index.abbreviation).filter(models.Index.abbreviation==index).one()
            except Exception:
                self.task_error = f'No index {index}'
            else:
                self.delete_index(index)

            index_index = next((ii for (ii, d) in enumerate(d.INDEXES) if d["abbreviation"] == index), -1)
            if index_index >= 0:
                ind = models.Index(abbreviation=index, name=d.INDEXES[index_index]['name'])
                session.add(ind)
                logger.info(f'{__name__}: Recreated index {index}')

                symbols = store.get_index_symbols_master(index)
                for symbol in symbols:
                    ticker = session.query(models.Security.ticker).filter(models.Security.ticker==symbol).one_or_none()
                    if ticker is not None:
                        valid += [ticker.ticker]

        if len(valid) > 0:
            self._add_securities_to_index(valid, index)
            logger.info(f'{__name__}: Populated index {index}')
            self.task_error = 'Done'
        elif not self.task_error:
            self.task_error = 'No symbols'
            logger.warning(f'{__name__}: No symbols found for {index}')

    def delete_index(self, index):
        with self.session.begin() as session:
            ind = session.query(models.Index).filter(models.Index.abbreviation==index)
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
                tables = models.Base.metadata.tables
                for table in tables:
                    count = session.query(tables[table]).count()
                    info += [{'table':table, 'count':count}]
        else:
            utils.print_error('No tables in database')
            logger.warning('{__name__}: No tables in database')

        return info

    def get_exchange_info(self):
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if len(tables) > 0:
            with self.session() as session:
                exchanges = session.query(models.Exchange).all()
                for e in exchanges:
                    s = session.query(models.Security).filter(models.Security.exchange_id == e.id)
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
                    indexes = session.query(models.Index)
                    for i in indexes:
                        s = session.query(models.Security).filter(or_(models.Security.index1_id == i.id, models.Security.index2_id == i.id))
                        info += [{'index':i.abbreviation, 'count':s.count()}]
                else:
                    i = session.query(models.Index).filter(models.Index.abbreviation == index).first()
                    s = session.query(models.Security).filter(or_(models.Security.index1_id == i.id, models.Security.index2_id == i.id))
                    info = [{'index':i.abbreviation, 'count':s.count()}]

        return info

    def identify_missing_securities(self, exchange, log=True):
        missing = []
        tickers = store.get_exchange_symbols_master(exchange)
        logger.info(f'{__name__}: {len(tickers)} total symbols in {exchange}')
        with self.session() as session:
            exc = session.query(models.Exchange.id, models.Exchange.abbreviation).filter(models.Exchange.abbreviation==exchange).one()
            for sec in tickers:
                t = session.query(models.Security.ticker).filter(and_(models.Security.ticker==sec, models.Security.exchange_id==exc.id)).one_or_none()
                if t is None:
                    missing += [sec]

        if log:
            filename = f'{LOG_DIR}/missing_securities_{exchange.upper()}.log'
            if len(missing) > 0:
                with open(filename, 'w') as f:
                    json.dump(missing, f, indent=2)
            elif os.path.exists(filename):
                os.remove(filename)

        logger.info(f'{__name__}: {len(missing)} missing symbols in {exchange}')
        return missing

    def identify_inactive_securities(self, exchange, log=True):
        missing = []
        tickers = store.get_symbols(exchange)
        if len(tickers) > 0:
            with self.session() as session:
                exc = session.query(models.Exchange.id, models.Exchange.abbreviation).filter(models.Exchange.abbreviation==exchange).one()
                for sec in tickers:
                    t = session.query(models.Security.ticker).filter(and_(models.Security.ticker==sec,
                        models.Security.exchange_id==exc.id, models.Security.active)).one_or_none()
                    if t is None:
                        missing += [sec]

        if log:
            filename = f'{LOG_DIR}/inactive_securities_{exchange.upper()}.log'
            if len(missing) > 0:
                with open(filename, 'w') as f:
                    json.dump(missing, f, indent=2)
            elif os.path.exists(filename):
                os.remove(filename)

        logger.info(f'{__name__}: {len(missing)} inactive symbols in {exchange}')
        return missing

    def identify_incomplete_securities_companies(self, exchange, live=False, log=True):
        missing = []
        if live:
            with self.session.begin() as session:
                exc = session.query(models.Exchange.id).filter(models.Exchange.abbreviation==exchange).one()
                sec = session.query(models.Security.ticker, models.Security.id).filter(models.Security.exchange_id==exc.id).all()
                for t in sec:
                    c = session.query(models.Company.id).filter(models.Company.security_id==t.id).limit(1)
                    if c.first() is None:
                        missing += [t.ticker]
                        mc = session.query(models.MissingCompany).filter(models.MissingCompany.security_id==t.id).one_or_none()
                        if mc is None:
                            mc = models.MissingCompany(security_id=t.id)
                            session.add(mc)
                        logger.info(f'{__name__}: {t.ticker} added missing company entry')

            if log:
                filename = f'{LOG_DIR}/incomplete_companies_{exchange.upper()}.log'
                if len(missing) > 0:
                    with open(filename, 'w') as f:
                        json.dump(missing, f, indent=2)
                elif os.path.exists(filename):
                    os.remove(filename)
        else:
            with self.session() as session:
                exc = session.query(models.Exchange.id).filter(models.Exchange.abbreviation==exchange).one()
                companies = session.query(models.MissingCompany).all()
                for company in companies:
                    sec = session.query(models.Security.ticker, models.Security.id).filter(
                        and_(models.Security.exchange_id==exc.id, models.Security.id==company.security_id)).one_or_none()
                    if sec is not None:
                        missing += [sec.ticker]

        logger.info(f'{__name__}: {len(missing)} with incomplete company info')
        return missing

    def identify_incomplete_securities_price(self, exchange, live=False, log=True):
        missing = []
        if live:
            with self.session.begin() as session:
                exc = session.query(models.Exchange.id).filter(models.Exchange.abbreviation==exchange).one()
                sec = session.query(models.Security.ticker, models.Security.id).filter(models.Security.exchange_id==exc.id).all()
                for t in sec:
                    c = session.query(models.Price.id).filter(models.Price.security_id==t.id).limit(1)
                    if c.first() is None:
                        missing += [t.ticker]
                        mc = session.query(models.MissingPrice.id).filter(models.MissingPrice.security_id==t.id).one_or_none()
                        if mc is None:
                            mc = models.MissingPrice(security_id=t.id)
                            session.add(mc)
                        logger.info(f'{__name__}: {t.ticker} added missing price entry')

            if log:
                filename = f'{LOG_DIR}/incomplete_price_{exchange.upper()}.log'
                if len(missing) > 0:
                    with open(filename, 'w') as f:
                        json.dump(missing, f, indent=2)
                elif os.path.exists(filename):
                    os.remove(filename)
        else:
            with self.session() as session:
                exc = session.query(models.Exchange.id).filter(models.Exchange.abbreviation==exchange).one()
                companies = session.query(models.MissingPrice).all()
                for company in companies:
                    sec = session.query(models.Security.ticker, models.Security.id).filter(
                        and_(models.Security.exchange_id==exc.id, models.Security.id==company.security_id)).one_or_none()
                    if sec is not None:
                        missing += [sec.ticker]

        logger.info(f'{__name__}: {len(missing)} incomplete symbol price info')
        return missing

    def identify_common_securities(self):
        nasdaq = store.get_exchange_symbols_master('NASDAQ')
        nyse = store.get_exchange_symbols_master('NYSE')
        amex = store.get_exchange_symbols_master('AMEX')

        nasdaq_nyse = nasdaq.intersection(nyse)
        nasdaq_amex = nasdaq.intersection(amex)
        nyse_amex = nyse.intersection(amex)

        return nasdaq_nyse, nasdaq_amex, nyse_amex

    def validate_list(self, list):
        symbols = []
        invalid = []
        if store.is_exchange(list):
            symbols = self.get_exchange_symbols_master(list)
        elif store.is_index(list):
            symbols = store.get_index_symbols_master(list)

        if len(symbols) > 0:
            for s in symbols:
                if not fetcher.validate_ticker(s):
                    invalid += [s]

        return invalid

    def _refresh_pricing(self, ticker, session):
        ticker = ticker.upper()
        today = date.today()
        days = 0

        history = store.get_history(ticker, 0)
        if history.empty:
            logger.warning(f'{__name__}: No price history')
        else:
            date_db = history['date']
            if date_db is not None:
                logger.info(f'{__name__}: Last {ticker} price in database: {date_db:%Y-%m-%d}')
            else:
                date_db = today - date(2000,1,1)
                logger.info(f'{__name__}: No date history for {ticker} in database')

            if (today - date_db).days > 1:
                history = store.get_history(ticker, 365, live=True)
                if history is None:
                    logger.info(f'{__name__}: No pricing information for {ticker}')
                elif history.empty:
                    logger.info(f'{__name__}: No pricing information for {ticker}')
                else:
                    date_cloud = history.iloc[-1]['date'].to_pydatetime().date()
                    logger.info(f'{__name__}: Last {ticker} price in cloud: {date_cloud:%Y-%m-%d}')

                    delta = (date_cloud - date_db).days
                    if delta > 1:
                        history = history[-delta:]
                        history.reset_index(inplace=True)
                        sec = session.query(models.Security).filter(models.Security.ticker==ticker).one()
                        days = delta
                        for _, price in history.iterrows():
                            if price['date']:
                                p = models.Price()
                                p.date = price['date']
                                p.open = price['open']
                                p.high = price['high']
                                p.low = price['low']
                                p.close = price['close']
                                p.volume = price['volume']

                                sec.pricing += [p]

                        logger.info(f'{__name__}: Updated {days} days pricing for {ticker.upper()} to {date_cloud:%Y-%m-%d}')
        return days

    def _add_securities_to_exchange(self, tickers, exchange):
        with self.session() as session:
            exc = session.query(models.Exchange).filter(models.Exchange.abbreviation==exchange).one()

            for sec in tickers:
                s = session.query(models.Security).filter(models.Security.ticker==sec).one_or_none()
                if s is None:
                    self.task_symbol = sec
                    exc.securities += [models.Security(sec)]
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
                            self.task_error = 'HTTP Error'
                            logger.error(f'{__name__}: HTTP Error. Too many retries. {str(e)}')
                        else:
                            time.sleep(5.0)
                    except RuntimeError as e:
                        self.task_error = 'Runtime Error'
                        logger.error(f'{__name__}: Runtime Error, {str(e)}')
                    else:
                        self.retry = 0
                        self.task_success += 1
                        logger.info(f'{__name__}: Added {sec} to exchange {exchange}')
                else:
                    logger.info(f'{__name__}: {sec} already exists')

                self.task_completed += 1

                if self.task_error != 'None':
                    logger.warning(f'{__name__}: Cancelling operation')
                    break

    def _add_company_to_security(self, ticker):
        added = False
        with self.session.begin() as session:
            sec = session.query(models.Security).filter(models.Security.ticker==ticker).one()
            company = store.get_company(ticker, live=True)
            if company is None:
                logger.info(f'{__name__}: No company for {ticker}')
            elif len(company) == 0:
                logger.info(f'{__name__}: No company information for {ticker}')
            else:
                c = models.Company()
                c.name = company['name'] if company['name'] else '<error>'
                c.description = company['description'][:4995]
                c.url = company['url']
                c.sector = company['sector']
                c.industry = company['industry']

                sec.company = [c]
                added = True
                logger.info(f'{__name__}: Added company information for {ticker}')

                # Remove from 'missing' table if there
                session.query(models.MissingCompany).filter(models.MissingCompany.security_id==sec.id).delete()

        return added

    def _add_pricing_to_security(self, ticker):
        added = False
        with self.session.begin() as session:
            sec = session.query(models.Security).filter(models.Security.ticker==ticker).one()
            history = store.get_history(ticker, -1, live=True)
            if history is None:
                sec.active = False
                logger.info(f'{__name__}: No pricing information for {ticker}')
            elif history.empty:
                sec.active = False
                logger.info(f'{__name__}: No pricing information for {ticker}')
            else:
                history.reset_index(inplace=True)
                for _, price in history.iterrows():
                    if price['date']:
                        p = models.Price()
                        p.date = price['date']
                        p.open = price['open']
                        p.high = price['high']
                        p.low = price['low']
                        p.close = price['close']
                        p.volume = price['volume']

                        sec.pricing += [p]
                        added = True
                        logger.info(f'{__name__}: Added pricing to {ticker}')

                        # Remove from 'missing' table if there
                        session.query(models.MissingPrice).filter(models.MissingPrice.security_id==sec.id).delete()
                    else:
                        sec.active = False

        return added

    def _add_securities_to_index(self, tickers, index):
        with self.session.begin() as session:
            ind = session.query(models.Index.id).filter(models.Index.abbreviation==index).one()

            self.task_total = len(tickers)
            for t in tickers:
                self.task_symbol = t
                self.task_success += 1

                s = session.query(models.Security).filter(models.Security.ticker==t).one()
                if s.index1_id is None:
                    s.index1_id = ind.id
                elif s.index2_id is None:
                    s.index2_id = ind.id
                elif s.index3_id is None:
                    s.index3_id = ind.id

                self.task_completed += 1

                logger.info(f'{__name__}: Added {t} to index {index}')


if __name__ == '__main__':
    # import sys
    from logging import DEBUG
    logger = utils.get_logger(DEBUG)

    manager = Manager()
    missing = manager._refresh_pricing('ibm')
    print(missing)

    # if len(sys.argv) > 1:
    #     data = manager.populate_exchange(sys.argv[1])
    # else:
    #     data = manager.populate_exchange('AMEX')

    # print(len(data))
    # invalid = manager.validate_list('NASDAQ')
    # print (invalid)

    # manager.delete_database(recreate=True)
    # manager.build_exchanges()
    # manager.build_indexes()
    # manager.populate_exchange('AMEX')
    # manager.populate_index('SP500')
    # manager.populate_index('DOW')
