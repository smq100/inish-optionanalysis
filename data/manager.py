import os
import time
import random
from datetime import date
from concurrent import futures
from urllib.error import HTTPError

from sqlalchemy import create_engine, inspect, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import numpy as np
import pandas as pd

from base import Threaded
import data as d
from data import store as store
from data import models as models
from utils import ui, logger

_logger = logger.get_logger()


class Manager(Threaded):
    def __init__(self):
        super().__init__()

        self.exchange = ''
        self.invalid_tickers = []
        self.retry = 0

        if d.ACTIVE_URI:
            self.engine = create_engine(d.ACTIVE_URI, echo=False)
            self.session = sessionmaker(bind=self.engine)

            # No multithreading for SQLite
            self._concurrency = 1 if d.ACTIVE_DB == 'SQLite' else 10
        else:
            raise ValueError('No database specified')

    def create_database(self) -> None:
        models.Base.metadata.create_all(self.engine)

    def create_exchanges(self) -> None:
        with self.session.begin() as session:
            for exchange in d.EXCHANGES:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange['abbreviation']).one_or_none()
                if e is None:
                    exc = models.Exchange(abbreviation=exchange['abbreviation'], name=exchange['name'])
                    session.add(exc)
                    _logger.info(f'{__name__}: Added exchange {exchange["abbreviation"]}')

    def create_indexes(self) -> None:
        with self.session.begin() as session:
            for index in d.INDEXES:
                i = session.query(models.Index.id).filter(models.Index.abbreviation == index['abbreviation']).one_or_none()
                if i is None:
                    ind = models.Index(abbreviation=index['abbreviation'], name=index['name'])
                    session.add(ind)
                    _logger.info(f'{__name__}: Added index {index["abbreviation"]}')

    @Threaded.threaded
    def populate_exchange(self, exchange: str) -> None:
        exchange = exchange.upper()
        running = self._concurrency

        def add(tickers):
            nonlocal running
            for ticker in tickers:
                self.task_ticker = ticker
                if self.add_ticker_to_exchange(ticker):
                    self.task_success += 1

                self.task_completed += 1

            running -= 1
            _logger.info(f'{__name__}: Thread completed. {running} threads remaining')

        if store.is_exchange(exchange):
            tickers = list(store.get_exchange_tickers_master(exchange))
            self.invalid_tickers = []
            self.retry = 0

            if len(tickers) > 10:
                self.task_total = len(tickers)
                self.task_error = 'None'

                with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                    if self._concurrency > 1:
                        random.shuffle(tickers)
                        lists = np.array_split(tickers, self._concurrency)
                        self.task_futures = [executor.submit(add, list, exchange) for list in lists]
                    else:
                        self.task_futures = [executor.submit(add, tickers, exchange)]
            else:
                _logger.warning(f'{__name__}: No symbols for {exchange}')

        self.task_error = 'Done'

    def add_ticker_to_exchange(self, ticker: str, exchange: str) -> bool:
        exchange = exchange.upper()
        exit = False
        process = False
        retries = 5
        success = False

        if store.is_exchange(exchange):
            with self.session() as session:
                exc = session.query(models.Exchange).filter(models.Exchange.abbreviation == exchange).one()
                sec = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()

                if sec is None:
                    process = False
                    company = store.get_company(ticker, live=True)
                    if company:
                        history = store.get_history(ticker, live=True)
                        if history is not None:
                            process = True
                        else:
                            self.invalid_tickers += [ticker]
                            _logger.warning(f'{__name__}: History information for {ticker} not available. Not added to database')
                    else:
                        self.invalid_tickers += [ticker]
                        _logger.warning(f'{__name__}: Company information for {ticker} not available. Not added to database')

                    if process:
                        try:
                            self.task_ticker = ticker
                            exc.securities += [models.Security(ticker)]
                            session.commit()

                            _logger.info(f'{__name__}: Added {ticker} to exchange {exchange}')

                            self._add_history_to_ticker(ticker, history=history)
                            self._add_company_to_ticker(ticker, company=company)
                        except (ValueError, KeyError, IndexError) as e:
                            self.invalid_tickers += [ticker]
                            _logger.warning(f'{__name__}: Company info invalid for {ticker}: {str(e)}')
                        except HTTPError as e:
                            self.retry += 1
                            _logger.warning(f'{__name__}: HTTP Error for {ticker}. Retry: {self.retry}: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers += [ticker]
                                exit = True
                                _logger.error(f'{__name__}: HTTP Error for {ticker}. Too many retries: {str(e)}')
                            else:
                                time.sleep(5.0)
                        except RuntimeError as e:
                            self.retry += 1
                            _logger.warning(f'{__name__}: Runtime Error for {ticker}. Retrying... {self.retry}: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers += [ticker]
                                exit = True
                                _logger.error(f'{__name__}: Runtime Error for {ticker}. Too many retries: {str(e)}')
                        except Exception as e:
                            self.retry += 1
                            _logger.warning(f'{__name__}: Error for {ticker}. Retrying... {self.retry}: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers += [ticker]
                                exit = True
                                _logger.error(f'{__name__}: Error for {ticker}. Too many retries: {str(e)}')
                        else:
                            self.retry = 0
                            success = True
                else:
                    _logger.info(f'{__name__}: {ticker} already exists')

                if exit:
                    _logger.error(f'{__name__}: Error adding ticker {ticker} to exchange')
        else:
            _logger.error(f'{__name__}: Exchange {exchange} does not exist')

        return success

    @Threaded.threaded
    def populate_index(self, index: str) -> None:
        index = index.upper()

        if store.is_index(index):
            self.task_error = 'None'

            # Delete and recreate the index
            with self.session.begin() as session:
                self.delete_index(index)

                index_index = next((ii for (ii, d) in enumerate(d.INDEXES) if d["abbreviation"] == index), -1)
                if index_index >= 0:
                    ind = models.Index(abbreviation=index, name=d.INDEXES[index_index]['name'])
                    session.add(ind)
                    _logger.info(f'{__name__}: Recreated index {index}')

            valid = []
            tickers = store.get_index_tickers_master(index)
            for ticker in tickers:
                t = session.query(models.Security.ticker).filter(models.Security.ticker == ticker).one_or_none()
                if ticker is not None:
                    valid += [t.ticker]

            if len(valid) > 0:
                self._add_securities_to_index(valid, index)
                _logger.info(f'{__name__}: Populated index {index}')
                self.task_error = 'Done'
            elif not self.task_error:
                self.task_error = 'No symbols'
                _logger.warning(f'{__name__}: No symbols found for {index}')
        else:
            self.task_error = f'No index {index}'
            _logger.warning(f'{__name__}: No valid index {index}')

    def update_company_ticker(self, ticker: str, replace=False) -> bool:
        updated = False
        if store.is_ticker(ticker):
            with self.session.begin() as session:
                t = session.query(models.Security).filter(models.Security.ticker == ticker).one()
                company = store.get_company(ticker, live=True)
                if company and ((company['name'] != store.UNAVAILABLE) or replace):
                    c = session.query(models.Company).filter(models.Company.security_id == t.id).one()
                    c.name = company['name']
                    c.description = company['description']
                    c.url = company['url']
                    c.sector = company['sector']
                    c.industry = company['industry']
                    c.beta = company['beta']
                    c.marketcap = company['marketcap']
                    c.rating = company['rating']

                    updated = True

                    _logger.info(f'{__name__}: Updated company information for {ticker}')
                else:
                    _logger.info(f'{__name__}: No company information for {ticker}')

        return updated

    @Threaded.threaded
    def update_companies_exchange(self, exchange: str, replace=False) -> None:
        exchange = exchange.upper()

        def update(tickers):
            nonlocal running
            for sec in tickers:
                self.task_ticker = sec
                if self.update_company_ticker(sec, replace=replace):
                    self.task_success += 1

                self.task_completed += 1

            running -= 1
            _logger.info(f'{__name__}: Thread completed. {running} threads remaining')

        if store.is_exchange(exchange):
            self.task_error = 'None'
            if replace:
                tickers = store.get_tickers(exchange)
            else:
                tickers = self.identify_incomplete_companies(exchange)

            self.task_total = len(tickers)
            concurrency = self._concurrency if self.task_total > self._concurrency else 1
            running = concurrency

            if self.task_total > 0:
                with futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                    if concurrency > 1:
                        random.shuffle(tickers)
                        lists = np.array_split(tickers, concurrency)
                        self.task_futures = [executor.submit(update, list) for list in lists]
                    else:
                        self.task_futures = [executor.submit(update, tickers)]

        self.task_error = 'Done'

    def update_history_ticker(self, ticker: str) -> int:
        ticker = ticker.upper()
        days = -1

        if store.is_ticker(ticker):
            today = date.today()

            history = store.get_history(ticker)
            if history.empty:
                if self._add_history_to_ticker(ticker):
                    _logger.info(f'{__name__}: Added full price history for {ticker}')
                    if self._add_company_to_ticker(ticker):
                        _logger.info(f'{__name__}: Added company information for {ticker}')
                else:
                    _logger.warning(f'{__name__}: No price history for {ticker}')
            else:
                date_db = history.iloc[-1]['date']
                if date_db is not None:
                    _logger.info(f'{__name__}: Last {ticker} price in database: {date_db:%Y-%m-%d}')
                else:
                    date_db = today - date(2000, 1, 1)
                    _logger.info(f'{__name__}: No price history for {ticker} in database')

                delta = (today - date_db).days
                if delta > 0:
                    history = store.get_history(ticker, 365, live=True)
                    if history is None:
                        _logger.info(f'{__name__}: No pricing dataframe for {ticker}')
                    elif history.empty:
                        _logger.info(f'{__name__}: Empty pricing dataframe for {ticker}')
                    else:
                        date_cloud = history.iloc[-1]['date'].to_pydatetime().date()
                        _logger.info(f'{__name__}: Last {ticker} price in cloud: {date_cloud:%Y-%m-%d}')

                        delta = (date_cloud - date_db).days
                        if delta > 0:
                            days = delta
                            history = history[-delta:]
                            history.reset_index(inplace=True)

                            with self.session.begin() as session:
                                t = session.query(models.Security).filter(models.Security.ticker == ticker).one()

                                for price in history.itertuples():
                                    if price.date:
                                        pri = session.query(models.Price.date).filter(and_(models.Price.security_id == t.id,
                                                                                           models.Price.date == price.date)).one_or_none()
                                        if pri is None:
                                            p = models.Price()
                                            p.date = price.date
                                            p.open = price.open
                                            p.high = price.high
                                            p.low = price.low
                                            p.close = price.close
                                            p.volume = price.volume

                                            t.pricing += [p]

                            _logger.info(f'{__name__}: Updated {days} days pricing for {ticker} to {date_cloud:%Y-%m-%d}')
                        else:
                            days = 0
                            _logger.info(f'{__name__}: {ticker} already up to date with cloud data')
                else:
                    _logger.info(f'{__name__}: {ticker} already up to date')
        else:
            _logger.info(f'{__name__}: Unknown ticker {ticker}')

        return days

    @Threaded.threaded
    def update_history_exchange(self, exchange: str) -> None:
        tickers = store.get_tickers(exchange)
        running = self._concurrency
        self.task_total = len(tickers)
        self.invalid_tickers = []

        def append(tickers: list[str]) -> None:
            nonlocal running
            for ticker in tickers:
                self.task_ticker = ticker
                try:
                    days = self.update_history_ticker(ticker)
                except IntegrityError as e:
                    _logger.warning(f'{__name__}: UniqueViolation exception occurred for {ticker}: {e}')

                self.task_completed += 1

                if days > 0:
                    self.task_success += 1
                elif days < 0:
                    self.invalid_tickers += [ticker]

            running -= 1
            _logger.info(f'{__name__}: Thread completed. {running} threads remaining')

        if self.task_total > 0:
            self.task_error = 'None'

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                if self._concurrency > 1:
                    random.shuffle(tickers)
                    lists = np.array_split(tickers, self._concurrency)
                    self.task_futures = [executor.submit(append, list) for list in lists]
                else:
                    self.task_futures = [executor.submit(append, tickers)]

        self.task_error = 'Done'

    def delete_database(self, recreate: bool = False):
        if d.ACTIVE_DB == d.VALID_DBS[1]:
            if os.path.exists(d.SQLITE_FILE_PATH):
                os.remove(d.SQLITE_FILE_PATH)
                _logger.info(f'{__name__}: Deleted {d.SQLITE_FILE_PATH}')
            else:
                _logger.warning(f'{__name__}: File does not exist: {d.SQLITE_FILE_PATH}')
        else:
            models.Base.metadata.drop_all(self.engine)

        if recreate:
            self.create_database()

    @Threaded.threaded
    def delete_exchange(self, exchange: str) -> None:
        exchange = exchange.upper()
        self.task_error = 'None'

        if store.is_exchange(exchange):
            with self.session.begin() as session:
                exc = session.query(models.Exchange).filter(models.Exchange.abbreviation == exchange.upper()).one_or_none()
                if exc is not None:
                    session.delete(exc)
                    _logger.info(f'{__name__}: Deleted exchange {exchange}')
                else:
                    _logger.warning(f'{__name__}: Exchange {exchange} does not exist')
        else:
            _logger.warning(f'{__name__}: Exchange {exchange} does not exist')
        self.task_error = 'Done'

    def delete_index(self, index: str) -> None:
        index = index.upper()

        if store.is_index(index):
            with self.session.begin() as session:
                ind = session.query(models.Index).filter(models.Index.abbreviation == index).one_or_none()

                if ind is not None:
                    session.delete(ind)
                    _logger.info(f'{__name__}: Deleted index {index}')
                else:
                    _logger.warning(f'{__name__}: Index {index} does not exist')
        else:
            _logger.warning(f'{__name__}: Index {index} does not exist')

    def delete_ticker(self, ticker: str) -> None:
        ticker = ticker.upper()

        if store.is_ticker(ticker):
            with self.session.begin() as session:
                sec = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
                if sec is not None:
                    session.delete(sec)

                    _logger.info(f'{__name__}: Deleted ticker {ticker}')
                else:
                    _logger.warning(f'{__name__}: Ticker {ticker} not in database')
        else:
            _logger.warning(f'{__name__}: Ticker {ticker} does not exist')

    def change_active(self, tickers: list[str], active: bool) -> None:
        if tickers:
            for ticker in tickers:
                ticker = ticker.upper()
                if store.is_ticker(ticker, inactive=True):
                    with self.session.begin() as session:
                        sec = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
                        if sec is not None:
                            sec.active = active
                            _logger.info(f'{__name__}: Set {ticker} active = {active}')
                        else:
                            _logger.warning(f'{__name__}: Ticker {ticker} not in database')
                else:
                    _logger.warning(f'{__name__}: Ticker {ticker} does not exist')

    def get_database_info(self) -> list[dict]:
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
            with self.session() as session:
                tables = models.Base.metadata.tables
                for table in tables:
                    count = session.query(tables[table]).count()
                    info += [{'table': table, 'count': count}]
        else:
            _logger.warning('{__name__}: No tables in database')

        return info

    def get_exchange_info(self) -> list[dict]:
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if len(tables) > 0:
            with self.session() as session:
                exchanges = session.query(models.Exchange).all()
                for e in exchanges:
                    s = session.query(models.Security).filter(models.Security.exchange_id == e.id)
                    if s is not None:
                        info += [{'exchange': e.abbreviation, 'count': s.count()}]

        return info

    def get_index_info(self, index: str = '') -> list[dict]:
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
            with self.session() as session:
                if not index:
                    indexes = session.query(models.Index)
                    for i in indexes:
                        s = session.query(models.Security).filter(or_(models.Security.index1_id == i.id,
                                                                      models.Security.index2_id == i.id, models.Security.index3_id == i.id))
                        info += [{'index': i.abbreviation, 'count': s.count()}]
                else:
                    i = session.query(models.Index).filter(models.Index.abbreviation == index).first()
                    s = session.query(models.Security).filter(or_(models.Security.index1_id == i.id,
                                                                  models.Security.index2_id == i.id, models.Security.index3_id == i.id))
                    info = [{'index': i.abbreviation, 'count': s.count()}]

        return info

    def list_exchange(self, exchange: str) -> list[str]:
        exchange = exchange.upper()
        found = []

        if store.is_exchange(exchange):
            with self.session() as session:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange).one()
                t = session.query(models.Security.ticker).filter(models.Security.exchange_id == e.id).order_by(models.Security.ticker).all()

                found = [ticker[0] for ticker in t]

            _logger.info(f'{__name__}: {len(found)} tickers in {exchange}')
        else:
            _logger.warning(f'{__name__}: {exchange} not valid')

        return found

    def list_index(self, index: str) -> list[str]:
        index = index.upper()
        found = []

        if store.is_index(index):
            with self.session() as session:
                i = session.query(models.Index.id).filter(models.Index.abbreviation == index).one()
                t = session.query(models.Security.ticker).filter(or_(models.Security.index1_id == i.id,
                                                                     models.Security.index2_id == i.id, models.Security.index3_id == i.id)).order_by(models.Security.ticker).all()

                found = [ticker[0] for ticker in t]

            _logger.info(f'{__name__}: {len(found)} tickers in {index}')
        else:
            _logger.warning(f'{__name__}: {index} not valid')

        return found

    def identify_missing_ticker(self, exchange: str) -> list[str]:
        exchange = exchange.upper()
        missing = []

        if store.is_exchange(exchange):
            tickers = store.get_exchange_tickers_master(exchange)
            _logger.info(f'{__name__}: {len(tickers)} total tickers in {exchange}')

            with self.session() as session:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange).one()
                for sec in tickers:
                    t = session.query(models.Security.ticker).filter(and_(models.Security.ticker == sec, models.Security.exchange_id == e.id)).one_or_none()
                    if t is None:
                        missing += [sec]

            _logger.info(f'{__name__}: {len(missing)} missing tickers in {exchange}')
        else:
            _logger.warning(f'{__name__}: {exchange} not valid')

        return missing

    def identify_inactive_tickers(self, exchange: str) -> list[str]:
        exchange = exchange.upper()
        inactive = []

        tickers = store.get_tickers(exchange, inactive=True)

        if len(tickers) > 0:
            with self.session() as session:
                if exchange == 'ALL':
                    for sec in tickers:
                        t = session.query(models.Security.ticker).filter(and_(models.Security.ticker == sec, models.Security.active == False)).one_or_none()
                        if t is not None:
                            inactive += [sec]
                else:
                    e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange).one()
                    for sec in tickers:
                        t = session.query(models.Security.ticker).filter(and_(models.Security.ticker == sec, models.Security.active == False, models.Security.exchange_id == e.id)).one_or_none()
                        if t is not None:
                            inactive += [sec]

            _logger.info(f'{__name__}: {len(inactive)} inactive tickers in {exchange}')
        else:
            _logger.warning(f'{__name__}: {exchange} not valid')

        return inactive

    @Threaded.threaded
    def identify_incomplete_pricing(self, table: str) -> dict:
        tickers = store.get_tickers(table.upper())
        running = self._concurrency
        self.task_total = len(tickers)
        self.task_object = {}

        def check(tickers: list[str]) -> None:
            nonlocal running
            for ticker in tickers:
                self.task_ticker = ticker
                history = store.get_history(ticker, days=90)
                if not history.empty:
                    date = f'{history.iloc[-1]["date"]:%Y-%m-%d}'
                    if date in self.task_object:
                        self.task_object[date] += [ticker]
                    else:
                        self.task_object[date] = [ticker]
                    self.task_success += 1
                self.task_completed += 1

            running -= 1
            _logger.info(f'{__name__}: Thread completed. {running} threads remaining')

        if self.task_total > 0:
            self.task_error = 'None'

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                if self._concurrency > 1:
                    random.shuffle(tickers)
                    lists = np.array_split(tickers, self._concurrency)
                    self.task_futures = [executor.submit(check, item) for item in lists]
                else:
                    self.task_futures = [executor.submit(check, tickers)]

            if len(self.task_object) > 1:
                last = sorted(self.task_object)[-1]
                self.task_object.pop(last)

            items = self.task_object.items()
            self.task_results = sorted(items)

        self.task_error = 'Done'

    def identify_incomplete_companies(self, table: str) -> list[str]:
        table = table.upper()
        incomplete = []
        tickers = []

        if store.is_exchange(table):
            tickers = store.get_exchange_tickers(table, inactive=True)
        elif store.is_index(table):
            tickers = store.get_index_tickers(table, inactive=True)
        else:
            _logger.warning(f'{__name__}: {table} is not valid exchange or index')

        if tickers:
            with self.session() as session:
                for ticker in tickers:
                    t = session.query(models.Security.id).filter(models.Security.ticker == ticker).one_or_none()
                    if t is not None:
                        c = session.query(models.Company.name).filter(models.Company.security_id == t.id).one_or_none()
                        if c is None:
                            incomplete += [ticker]
                        elif c.name == store.UNAVAILABLE:
                            incomplete += [ticker]

        _logger.info(f'{__name__}: {len(incomplete)} incomplete companies in {table}')

        return incomplete

    def _add_company_to_ticker(self, ticker: str, company: dict = None) -> bool:
        cmp = None

        with self.session.begin() as session:
            t = session.query(models.Security).filter(models.Security.ticker == ticker).one()
            if company is None:
                company = store.get_company(ticker, live=True)

            if company:
                cmp = models.Company()
                cmp.name = company['name']
                cmp.description = company['description']
                cmp.url = company['url']
                cmp.sector = company['sector']
                cmp.industry = company['industry']
                cmp.beta = company['beta']
                cmp.marketcap = company['marketcap']
                cmp.rating = company['rating']

                t.company = [cmp]
                _logger.info(f'{__name__}: Added company information for {ticker}')
            else:
                _logger.warning(f'{__name__}: No company info for {ticker}')

        return cmp is not None

    def _add_history_to_ticker(self, ticker: str, history: pd.DataFrame = None) -> bool:
        added = False

        with self.session.begin() as session:
            t = session.query(models.Security).filter(models.Security.ticker == ticker).one()

            if history is None or history.empty:
                history = store.get_history(ticker, live=True)

            if history is not None and not history.empty:
                history.reset_index(inplace=True)
                try:
                    for price in history.itertuples():
                        if price.date:
                            p = models.Price()
                            p.date = price.date
                            p.open = price.open
                            p.high = price.high
                            p.low = price.low
                            p.close = price.close
                            p.volume = price.volume

                            t.pricing += [p]
                            added = True
                        else:
                            t.active = False
                except IntegrityError as e:
                    _logger.info(f'{__name__}: {ticker} UniqueViolation exception occurred for {ticker}: {e}')
                else:
                    _logger.info(f'{__name__}: Added pricing information for {ticker}')
            else:
                t.active = False
                _logger.warning(f'{__name__}: No pricing information for {ticker}')

        return added

    def _add_securities_to_index(self, tickers: list[str], index: str) -> None:
        with self.session.begin() as session:
            ind = session.query(models.Index.id).filter(models.Index.abbreviation == index).one()

            self.task_total = len(tickers)
            for t in tickers:
                self.task_ticker = t
                self.task_success += 1

                s = session.query(models.Security).filter(models.Security.ticker == t).one()
                if s.index1_id is None:
                    s.index1_id = ind.id
                elif s.index2_id is None:
                    s.index2_id = ind.id
                elif s.index3_id is None:
                    s.index3_id = ind.id

                self.task_completed += 1

                _logger.info(f'{__name__}: Added {t} to index {index}')


if __name__ == '__main__':
    import time
    from logging import DEBUG
    _logger = ui.get_logger(DEBUG)

    manager = Manager()
    tic = time.perf_counter()
    missing = manager.identify_incomplete_pricing('AMEX')
    toc = time.perf_counter()
    timed = toc - tic

    print(f'Found {missing} in {timed:.2f} seconds')
