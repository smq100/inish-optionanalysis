import time
import random
import datetime as dt
from concurrent import futures
from pathlib import Path
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
            self._concurrency = 1 if (d.ACTIVE_DB == 'SQLite' or d.DEBUG_DB) else 10
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
                    _logger.info(f'Added exchange {exchange["abbreviation"]}')

    def create_indexes(self) -> None:
        with self.session.begin() as session:
            for index in d.INDEXES:
                i = session.query(models.Index.id).filter(models.Index.abbreviation == index['abbreviation']).one_or_none()
                if i is None:
                    ind = models.Index(abbreviation=index['abbreviation'], name=index['name'])
                    session.add(ind)
                    _logger.info(f'Added index {index["abbreviation"]}')

    @Threaded.threaded
    def populate_exchange(self, exchange: str, log: bool = True) -> None:
        exchange = exchange.upper()
        running = self._concurrency

        def add(tickers):
            for ticker in tickers:
                self.task_ticker = ticker
                if self.add_ticker_to_exchange(ticker, exchange):
                    self.task_success += 1

                self.task_completed += 1

        if store.is_exchange(exchange):
            tickers = store.get_exchange_tickers_master(exchange)
            self.invalid_tickers = []
            self.retry = 0

            if tickers:
                self.task_total = len(tickers)
                self.task_state = 'None'

                with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                    random.shuffle(tickers)
                    if d.DEBUG_DB:
                        tickers = tickers[:10]
                        self.task_futures = [executor.submit(add, tickers)]
                    elif self._concurrency > 1:
                        lists = np.array_split(tickers, self._concurrency)
                        lists = [item.tolist() for item in lists if item.size > 0]
                        self.task_futures = [executor.submit(add, item) for item in lists]
                    else:
                        self.task_futures = [executor.submit(add, tickers)]

                    for future in futures.as_completed(self.task_futures):
                        running -= 1
                        _logger.debug(f'Thread completed: {future.result()}. {running} threads remaining')
            else:
                _logger.warning(f'No symbols for {exchange}')
        else:
            _logger.warning(f'\'{exchange}\' is not a valid exchange')

        if log:
            ui.write_tickers_log(self.invalid_tickers)

        self.task_state = 'Done'

    def add_ticker_to_exchange(self, ticker: str, exchange: str) -> bool:
        exchange = exchange.upper()
        exit = False
        retries = 2
        process = False
        success = False

        if store.is_exchange(exchange):
            with self.session() as session:
                exc = session.query(models.Exchange).filter(models.Exchange.abbreviation == exchange).one()
                tic = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()

                if tic is None:
                    process = False
                    company = store.get_company(ticker, live=True)
                    if company:
                        history = store.get_history(ticker, live=True)
                        if history is None:
                            self.invalid_tickers.append(ticker)
                            _logger.error(f'\'None\' object for {ticker}')
                        elif history.empty:
                            self.invalid_tickers.append(ticker)
                            _logger.warning(f'History for {ticker} not available. Not added to database')
                        else:
                            process = True
                    else:
                        self.invalid_tickers.append(ticker)
                        _logger.warning(f'Company for {ticker} not available. Not added to database')

                    if process:
                        try:
                            self.task_ticker = ticker
                            exc.securities.append(models.Security(ticker))
                            session.commit()

                            _logger.info(f'Added {ticker} to exchange {exchange}')

                            self._add_live_history_to_ticker(ticker, history=history)
                            self._add_live_company_to_ticker(ticker, company=company)
                        except (ValueError, KeyError, IndexError) as e:
                            self.invalid_tickers.append(ticker)
                            _logger.warning(f'Company info invalid for {ticker}: {str(e)}')
                        except HTTPError as e:
                            self.retry += 1
                            _logger.warning(f'HTTP Error for {ticker}. Retrying {self.retry}...: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers.append(ticker)
                                exit = True
                                _logger.error(f'HTTP Error for {ticker}. Too many retries: {str(e)}')
                            else:
                                time.sleep(1.0)
                        except RuntimeError as e:
                            self.retry += 1
                            _logger.warning(f'Runtime Error for {ticker}. Retrying {self.retry}...: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers.append(ticker)
                                exit = True
                                _logger.error(f'Runtime Error for {ticker}. Too many retries: {str(e)}')
                        except Exception as e:
                            self.retry += 1
                            _logger.warning(f'Error for {ticker}. Retrying {self.retry}...: {str(e)}')
                            if self.retry > retries:
                                self.invalid_tickers.append(ticker)
                                exit = True
                                _logger.error(f'Error for {ticker}. Too many retries: {str(e)}')
                        else:
                            self.retry = 0
                            success = True
                else:
                    _logger.info(f'{ticker} already exists. Skipped')

                if exit:
                    _logger.error(f'Error adding ticker {ticker} to exchange')
        else:
            _logger.error(f'Exchange {exchange} does not exist')

        return success

    @Threaded.threaded
    def populate_index(self, index: str) -> None:
        index = index.upper()

        if store.is_index(index):
            self.task_state = 'None'

            # Delete and recreate the index
            with self.session.begin() as session:
                self.delete_index(index)

                index_index = next((ii for (ii, d) in enumerate(d.INDEXES) if d["abbreviation"] == index), -1)
                if index_index >= 0:
                    ind = models.Index(abbreviation=index, name=d.INDEXES[index_index]['name'])
                    session.add(ind)
                    _logger.info(f'Recreated index {index}')

            valid = []
            tickers = store.get_index_tickers_master(index)
            for ticker in tickers:
                t = session.query(models.Security.ticker).filter(models.Security.ticker == ticker).one_or_none()
                if t is not None:
                    valid.append(t.ticker)

            if len(valid) > 0:
                self._add_securities_to_index(valid, index)
                _logger.info(f'Populated index {index}')
                self.task_state = 'Done'
            elif not self.task_state:
                self.task_state = 'No symbols'
                _logger.warning(f'No symbols found for {index}')
        else:
            self.task_state = f'No index {index}'
            _logger.warning(f'No valid index {index}')

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

                    _logger.info(f'Updated company information for {ticker}')
                else:
                    _logger.warning(f'No company information for {ticker}')

        return updated

    @Threaded.threaded
    def update_companies_exchange(self, exchange: str, replace=False) -> None:
        exchange = exchange.upper()

        def update(tickers):
            for sec in tickers:
                self.task_ticker = sec
                if self.update_company_ticker(sec, replace=replace):
                    self.task_success += 1

                self.task_completed += 1

        if store.is_exchange(exchange):
            self.task_state = 'None'
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
                        lists = [item.tolist() for item in lists if item.size > 0]
                        self.task_futures = [executor.submit(update, item) for item in lists]
                    else:
                        self.task_futures = [executor.submit(update, tickers)]

                    for future in futures.as_completed(self.task_futures):
                        running -= 1
                        _logger.info(f'Thread completed: {future.result()}. {running} threads remaining')

        self.task_state = 'Done'

    def update_history_ticker(self, ticker: str, inactive: bool = False) -> int:
        ticker = ticker.upper()
        days = -1

        if store.is_ticker(ticker, inactive):
            today = dt.date.today()

            history = store.get_history(ticker, inactive=inactive)
            if history is None:
                _logger.error(f'\'None\' object for {ticker}')
            elif history.empty:
                if self._add_live_history_to_ticker(ticker):
                    _logger.info(f'Added full price history for {ticker}')

                    self._add_live_company_to_ticker(ticker)
                else:
                    _logger.warning(f'No price history for {ticker}')
            else:
                date_db = history.iloc[-1]['date']
                if date_db is None:
                    date_db = today - dt.date(2000, 1, 1)
                    _logger.warning(f'No price history for {ticker} in database')

                delta = (today - date_db).days
                if delta > 0:
                    history = store.get_history(ticker, days=60, live=True)  # Change days value if severely out of data
                    if history is None:
                        _logger.error(f'\'None\' object for {ticker}')
                    elif history.empty:
                        _logger.warning(f'Empty pricing dataframe for {ticker}')
                    else:
                        date_cloud = history.iloc[-1]['date'].to_pydatetime().date()
                        delta = (date_cloud - date_db).days
                        _logger.info(f'Last {ticker} price in database: {date_db:%Y-%m-%d}')
                        _logger.info(f'Last {ticker} price in cloud: {date_cloud:%Y-%m-%d}')
                        _logger.info(f'{date_cloud:%Y-%m-%d} - {date_db:%Y-%m-%d} = {delta} days')
                        if delta > 0:
                            days = delta
                            history = history[-delta:]
                            history = history.reset_index()

                            with self.session.begin() as session:
                                t = session.query(models.Security).filter(models.Security.ticker == ticker).one()

                                # Add any newer price records
                                for price in history.itertuples():
                                    date = price.date.to_pydatetime().date()
                                    if date > date_db:
                                        q = session.query(models.Price.date).filter(and_(models.Price.security_id == t.id, models.Price.date == date)).one_or_none()
                                        if q is None:
                                            p = models.Price()
                                            p.date = date
                                            p.open = price.open
                                            p.high = price.high
                                            p.low = price.low
                                            p.close = price.close
                                            p.volume = price.volume

                                            t.pricing += [p]

                            _logger.info(f'Updated {days} days pricing for {ticker} to {date_cloud:%Y-%m-%d}')
                        else:
                            days = 0
                            _logger.info(f'{ticker} already up to date with cloud data')
                else:
                    _logger.info(f'{ticker} already up to date')
        else:
            _logger.warning(f'Unknown ticker {ticker}')

        return days

    @Threaded.threaded
    def update_history_exchange(self, exchange: str, log: bool = True) -> None:
        tickers = store.get_tickers(exchange)
        self.invalid_tickers = []
        self.task_total = len(tickers)
        running = self._concurrency

        def update(tickers: list[str]) -> None:
            for ticker in tickers:
                tic = time.perf_counter()
                self.task_ticker = ticker
                days = -1

                try:
                    time.sleep(0.05)
                    days = self.update_history_ticker(ticker)
                except IntegrityError as e:
                    _logger.error(f'IntegrityError exception occurred for {ticker}: {e.__cause__}')
                except Exception as e:
                    _logger.error(f'Unknown exception occurred for {ticker}: {e}')

                self.task_completed += 1

                if days > 0:
                    self.task_success += 1
                    self.task_counter += days
                elif days < 0:
                    self.invalid_tickers.append(ticker)
                    _logger.warning(f'No data for {ticker}')

                    if log:
                        ui.write_tickers_log(self.invalid_tickers)

                toc = time.perf_counter()
                _logger.debug(f'{toc-tic:.2f}s to update {ticker}')

        if self.task_total > 0:
            self.task_state = 'None'

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                if self._concurrency > 1:
                    random.shuffle(tickers)
                    lists = np.array_split(tickers, self._concurrency)
                    lists = [item.tolist() for item in lists if item.size > 0]
                    self.task_futures = [executor.submit(update, item) for item in lists]
                else:
                    self.task_futures = [executor.submit(update, tickers)]

                for future in futures.as_completed(self.task_futures):
                    running -= 1
                    _logger.info(f'Thread completed: {future.result()}. {running} threads remaining')
        if log:
            ui.write_tickers_log(self.invalid_tickers)

        self.task_state = 'Done'

    def delete_database(self, recreate: bool = False):
        if d.ACTIVE_DB == d.VALID_DBS[1]: # Postfres
            models.Base.metadata.drop_all(self.engine)
        elif d.ACTIVE_DB == d.VALID_DBS[2]: # SQLite
            path = Path(d.SQLITE_FILE_PATH)
            if path.is_file():
                path.unlink()
                _logger.info(f'Deleted {d.SQLITE_FILE_PATH}')
            else:
                _logger.error(f'File does not exist: {d.SQLITE_FILE_PATH}')
        else:
            recreate = False

        if recreate:
            self.create_database()

    def delete_exchange(self, exchange: str) -> None:
        exchange = exchange.upper()
        self.task_state = 'None'

        if store.is_exchange(exchange):
            with self.session.begin() as session:
                exc = session.query(models.Exchange).filter(models.Exchange.abbreviation == exchange.upper()).one_or_none()
                if exc is not None:
                    session.delete(exc)
                    _logger.info(f'Deleted exchange {exchange}')
                else:
                    _logger.warning(f'Exchange {exchange} does not exist')
        else:
            _logger.warning(f'Exchange {exchange} does not exist')
        self.task_state = 'Done'

    def delete_index(self, index: str) -> None:
        index = index.upper()

        if store.is_index(index):
            with self.session.begin() as session:
                ind = session.query(models.Index).filter(models.Index.abbreviation == index).one_or_none()

                if ind is not None:
                    session.delete(ind)
                    _logger.info(f'Deleted index {index}')
                else:
                    _logger.warning(f'Index {index} does not exist')
        else:
            _logger.warning(f'Index {index} does not exist')

    def delete_ticker(self, ticker: str) -> None:
        ticker = ticker.upper()

        if store.is_ticker(ticker):
            with self.session.begin() as session:
                sec = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
                if sec is not None:
                    session.delete(sec)

                    _logger.info(f'Deleted ticker {ticker}')
                else:
                    _logger.warning(f'Ticker {ticker} not in database')
        else:
            _logger.warning(f'Ticker {ticker} does not exist')

    def change_active(self, tickers: list[str], active: bool) -> None:
        if tickers:
            for ticker in tickers:
                ticker = ticker.upper()
                if store.is_ticker(ticker, inactive=True):
                    with self.session.begin() as session:
                        sec = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()
                        if sec is not None:
                            sec.active = active
                            _logger.info(f'Set {ticker} active = {active}')
                        else:
                            _logger.warning(f'Ticker {ticker} not in database')
                else:
                    _logger.warning(f'Ticker {ticker} does not exist')

    def is_active(self, ticker: str) -> bool:
        active = False
        if ticker:
            if store.is_ticker(ticker, inactive=True):
                with self.session() as session:
                    sec = session.query(models.Security.active).filter(models.Security.ticker == ticker).one_or_none()
                    active = sec.active

        return active

    def get_database_info(self) -> list[dict]:
        info = []
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        if (len(tables) > 0):
            with self.session() as session:
                tables = models.Base.metadata.tables
                for table in tables:
                    count = session.query(tables[table]).count()
                    info.append({'table': table, 'count': count})
        else:
            _logger.warning('No tables in database')

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
                        info.append({'exchange': e.abbreviation, 'count': s.count()})

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
                        info.append({'index': i.abbreviation, 'count': s.count()})
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

            _logger.info(f'{len(found)} tickers in {exchange}')
        else:
            _logger.warning(f'{exchange} not valid')

        return found

    def list_index(self, index: str) -> list[str]:
        index = index.upper()
        found = []

        if store.is_index(index):
            with self.session() as session:
                i = session.query(models.Index.id).filter(models.Index.abbreviation == index).one()
                t = session.query(models.Security.ticker).filter(
                    or_(models.Security.index1_id == i.id, models.Security.index2_id == i.id, models.Security.index3_id == i.id)).order_by(models.Security.ticker).all()

                found = [ticker[0] for ticker in t]

            _logger.info(f'{len(found)} tickers in {index}')
        else:
            _logger.warning(f'{index} not valid')

        return found

    def get_latest_errors(self) -> list[str]:
        errors = []
        files = []

        path = Path(ui.LOG_DIR)
        items = [item for item in path.glob(f'*.{ui.LOG_SUFFIX}') if item.is_file()]
        for item in items:
            head, sep, tail = item.name.partition('.')
            if head[:2] == '20':
                files.append(f'{ui.LOG_DIR}/{item.name}')

        if files:
            files.sort()
            errors = ui.read_tickers_log(files[-1])

        return errors

    @Threaded.threaded
    def recheck_inactive(self, tickers: list[str]) -> None:
        self.task_total = len(tickers)

        def recheck(tickers: list[str]) -> None:
            for ticker in tickers:
                if not self.is_active(ticker):
                    self.task_ticker = ticker
                    try:
                        days = self.update_history_ticker(ticker, inactive=True)
                    except IntegrityError as e:
                        _logger.error(f'IntegrityError exception occurred for {ticker}: {e.__cause__}')
                    except Exception as e:
                        _logger.error(f'Unknown exception occurred for {ticker}: {e}')
                    else:
                        if days > 0:
                            self.task_results.append(ticker)
                            self.task_success += 1
                            _logger.info(f'Ticker {ticker} updated')
                        elif days < 0:
                            self.invalid_tickers.append(ticker)
                            _logger.info(f'Ticker {ticker} not updated')

                self.task_completed += 1

        if self.task_total > 1:
            self.task_state = 'None'

            random.shuffle(tickers)
            lists = np.array_split(tickers, self._concurrency)
            lists = [item.tolist() for item in lists if item.size > 0]
            running = len(lists)
            if running < self._concurrency:
                self._concurrency = running

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                if self._concurrency > 1:
                    self.task_futures = [executor.submit(recheck, item) for item in lists]
                else:
                    running = 1
                    self.task_futures = [executor.submit(recheck, tickers)]

                for future in futures.as_completed(self.task_futures):
                    running -= 1
                    _logger.info(f'Thread completed: {future.result()}. {running} threads remaining')
        elif tickers:
            recheck(tickers)

        self.task_state = 'Done'

    def identify_missing_ticker(self, exchange: str) -> list[str]:
        exchange = exchange.upper()
        missing = []

        if store.is_exchange(exchange):
            tickers = store.get_exchange_tickers_master(exchange)
            _logger.info(f'{len(tickers)} total tickers in {exchange}')

            with self.session() as session:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange).one()
                for sec in tickers:
                    t = session.query(models.Security.ticker).filter(and_(models.Security.ticker == sec, models.Security.exchange_id == e.id)).one_or_none()
                    if t is None:
                        missing.append(sec)

            _logger.info(f'{len(missing)} missing tickers in {exchange}')
        else:
            _logger.warning(f'{exchange} not valid')

        return missing

    def identify_inactive_tickers(self, exchange: str) -> list[str]:
        exchange = exchange.upper()

        inactive = []
        with self.session() as session:
            if exchange == 'EVERY':
                tickers = session.query(models.Security.ticker).filter(models.Security.active == False).all()
            else:
                e = session.query(models.Exchange.id).filter(models.Exchange.abbreviation == exchange).one()
                tickers = session.query(models.Security.ticker).filter(and_(models.Security.exchange_id == e.id, models.Security.active == False)).all()

        if tickers:
            inactive = [symbol.ticker for symbol in tickers]

        _logger.info(f'{len(inactive)} inactive tickers in {exchange}')

        return inactive

    @Threaded.threaded
    def identify_incomplete_pricing(self, table: str , days: int = 7) -> None:
        tickers = store.get_tickers(table.upper())
        running = self._concurrency
        self.task_total = len(tickers)
        self.task_object: dict = {}

        def check(tickers: list[str]) -> None:
            for ticker in tickers:
                self.task_ticker = ticker
                history = store.get_history(ticker, days=90)
                if history is None:
                    _logger.error(f'\'None\' object for {ticker}')
                elif not history.empty:
                    last = history.iloc[-1].date
                    past = dt.datetime.today() - dt.timedelta(days=days)
                    date = f'{last:%Y-%m-%d}'
                    if last < past.date():
                        if date in self.task_object:
                            self.task_object[date].append(ticker)
                        else:
                            self.task_object[date] = [ticker]
                        self.task_success += 1
                self.task_completed += 1

        if self.task_total > 0:
            self.task_state = 'None'

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                if self._concurrency > 1:
                    random.shuffle(tickers)
                    lists = np.array_split(tickers, self._concurrency)
                    lists = [item.tolist() for item in lists if item.size > 0]
                    self.task_futures = [executor.submit(check, item) for item in lists]
                else:
                    self.task_futures = [executor.submit(check, tickers)]

                for future in futures.as_completed(self.task_futures):
                    running -= 1
                    _logger.info(f'Thread completed: {future.result()}. {running} threads remaining')

            if len(self.task_object) > 1:
                last = sorted(self.task_object)[-1]
                self.task_object.pop(last)

            items = self.task_object.items()
            self.task_results = sorted(items)

        self.task_state = 'Done'

    def identify_incomplete_companies(self, table: str) -> list[str]:
        table = table.upper()
        incomplete = []
        tickers = []

        if store.is_exchange(table):
            tickers = store.get_exchange_tickers(table, inactive=True)
        elif store.is_index(table):
            tickers = store.get_index_tickers(table, inactive=True)
        else:
            _logger.warning(f'{table} is not valid exchange or index')

        if tickers:
            with self.session() as session:
                for ticker in tickers:
                    t = session.query(models.Security.id).filter(models.Security.ticker == ticker).one_or_none()
                    if t is not None:
                        c = session.query(models.Company.name).filter(models.Company.security_id == t.id).one_or_none()
                        if c is None:
                            incomplete.append(ticker)
                        elif c.name == '':
                            incomplete.append(ticker)

        _logger.info(f'{len(incomplete)} incomplete companies in {table}')

        return incomplete

    def _add_live_company_to_ticker(self, ticker: str, company: dict | None = None) -> bool:
        c = None

        try:
            with self.session.begin() as session:
                t = session.query(models.Security).filter(models.Security.ticker == ticker).one()

                if company is None:
                    company = store.get_company(ticker, live=True)

                if company:
                    c = models.Company()
                    c.name = company.get('name', '')
                    c.description = company.get('description', '')
                    c.url = company.get('url', '')
                    c.sector = company.get('sector', '')
                    c.industry = company.get('industry', '')
                    c.marketcap = company.get('marketcap', 0)
                    c.beta = company.get('beta', 0.0)
                    c.rating = company.get('rating', 3.0)
                    t.company = [c]

                    _logger.info(f'Added company information for {ticker}')
                else:
                    _logger.warning(f'No company info for {ticker}')
        except IntegrityError as e:
            c = None
            _logger.error(f'IntegrityError exception occurred for {ticker}: {e.__cause__}')
        except Exception as e:
            c = None
            _logger.error(f'Unknown exception occurred for {ticker}: {e}')

        return c is not None

    def _add_live_history_to_ticker(self, ticker: str, history: pd.DataFrame | None = None) -> bool:
        added = False

        try:
            with self.session.begin() as session:
                t = session.query(models.Security).filter(models.Security.ticker == ticker).one_or_none()

                if t is not None:
                    if history is None or history.empty:
                        history = store.get_history(ticker, live=True)

                    if history is None:
                        _logger.error(f'\'None\' object for {ticker}')
                    if not history.empty:
                        for price in history.reset_index().itertuples():
                            if price.date:
                                p = models.Price()
                                p.date = price.date
                                p.open = price.open
                                p.high = price.high
                                p.low = price.low
                                p.close = price.close
                                p.volume = price.volume

                                t.pricing += [p]
                            else:
                                t.active = False
                        else:
                            _logger.info(f'Added pricing information for {ticker}')
                    else:
                        t.active = False
                        _logger.info(f'No pricing information for {ticker}')
                else:
                    _logger.warning(f'{ticker} is not a valid ticker')
        except IntegrityError as e:
            _logger.error(f'IntegrityError exception occurred for {ticker}: {e.__cause__}')
        except Exception as e:
            _logger.error(f'Unknown exception occurred for {ticker}: {e}')
        else:
            added = True

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

                _logger.info(f'Added {t} to index {index}')


if __name__ == '__main__':
    import sys
    import logging

    logger.get_logger(logging.DEBUG)

    m = Manager()

    if len(sys.argv) > 1:
        c = m.add_ticker_to_exchange(sys.argv[1], 'NASDAQ')
    else:
        c = m.add_ticker_to_exchange('AAPL', 'NASDAQ')
