import os
import json
import pickle
import random
import datetime as dt
from concurrent import futures
from dataclasses import dataclass

import numpy as np
import pandas as pd

from base import Threaded
from company.company import Company
from data import store as store
from .interpreter import Interpreter
from utils import ui, logger


_logger = logger.get_logger()

SCREEN_BASEPATH = './screener/screens/'
SCREEN_SUFFIX = 'screen'
SCREEN_INIT_NAME = 'init'

CACHE_BASEPATH = './screener/cache/'
CACHE_SUFFIX = 'pickle'


@dataclass
class Result:
    company: Company
    screen: str
    successes: list[bool]
    scores: list[float]
    descriptions: list[str]
    price_current: float
    price_last: float = 0.0
    backtest_success: bool = False

    def __repr__(self):
        return f'{self.company.ticker}: {float(self):.2f}, {self.screen}'

    def __str__(self):
        return self.company.ticker

    def __bool__(self):
        return all(self.successes)

    def __float__(self):
        return float(sum(self.scores)) / len(self.scores) if len(self.scores) > 0 else 0.0


class Screener(Threaded):
    def __init__(self, table: str, screen: str, days: int = 365, backtest: int = 0, live: bool = False):
        if not table:
            raise ValueError('Table not specified')
        if not screen:
            raise ValueError('Screen not specified')
        if days < 30:
            raise ValueError('Invalid number of days')
        if backtest < 0:
            raise ValueError('Invalid backtest days')

        super().__init__()

        self.table = table.upper()
        self.screen = screen
        self.days = days
        self.backtest = backtest
        self.live = live if store.is_database_connected() else True

        if self.table == 'EVERY':
            self.type = 'every'
        elif store.is_exchange(self.table):
            self.type = 'exchange'
        elif store.is_index(self.table):
            self.type = 'index'
        elif store.is_ticker(table):
            self.type = 'symbol'
        else:
            self.type = ''
            raise ValueError(f'Table not found: {self.table}')

        self.screen_init = f'{SCREEN_BASEPATH}{SCREEN_INIT_NAME}.{SCREEN_SUFFIX}'
        self.cache_available = False
        self.cache_used = False
        self.scripts: list[dict] = []
        self.companies: list[Company] = []
        self.results: list[Result] = []
        self.valids: list[Result] = []
        self.errors: list[Result] = []
        self.summary: pd.DataFrame = pd.DataFrame()
        self.concurrency = 10

        if self._load(screen, init=self.screen_init):
            self._open()
            self.cache_available = self._load_results() if self.backtest == 0 else False
        else:
            raise ValueError(f'Script not found or invalid format: {screen}')

    def __repr__(self):
        return f'<Screener ({self.table} - {self.screen})>'

    def __str__(self):
        return f'{self.table} - {self.screen}'

    @Threaded.threaded
    def run_script(self, use_cache: bool = True, save_results: bool = True) -> None:
        self.task_total = len(self.companies)

        if use_cache and self.cache_available:
            self.valids = [result for result in self.results if result]
            self.valids = sorted(self.valids, reverse=True, key=lambda r: float(r))
            self.task_completed = self.task_total
            self.task_success = len(self.valids)
            self.task_state = 'Done'
            self.cache_used = True
            _logger.info(f'{__name__}: Using cached results')
        elif self.task_total == 0:
            self.results = []
            self.valids = []
            self.task_completed = self.task_total
            self.task_state = 'No symbols'
            _logger.warning(f'{__name__}: {self.task_state}')
        elif len(self.scripts) == 0:
            self.results = []
            self.valids = []
            self.task_completed = self.task_total
            self.task_state = 'Illegal script'
            _logger.warning(f'{__name__}: {self.task_state}')
        else:
            self.results = []
            self.valids = []
            self.errors = []
            self.task_state = 'None'
            self.concurrency = 10 if len(self.companies) > 10 else 1

            if self.task_total > 1:
                _logger.info(f'{__name__}: Screening {self.task_total} symbols from {self.table} table (days={self.days}, end={self.backtest})')
            else:
                _logger.info(f'{__name__}: Screening {self.table} (days={self.days}, end={self.backtest})')

            # Randomize and split up the lists
            random.shuffle(self.companies)
            companies: list[np.ndarray] = np.array_split(self.companies, self.concurrency)
            companies = [i.tolist() for i in companies if i is not None]

            with futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                self.task_futures = [executor.submit(self._run, list) for list in companies]

                for future in futures.as_completed(self.task_futures):
                    _logger.info(f'{__name__}: Thread completed: {future.result()}')

            # Extract the successful screens, sort based on score, then summarize
            self.valids = [result for result in self.results if result]
            self.valids = sorted(self.valids, reverse=True, key=lambda r: float(r))
            self.summary = summarize(self.valids)

            if save_results:
                self._save_results()

            self.task_state = 'Done'

    def get_score(self, ticker: str) -> float:
        ticker = ticker.upper()
        score = -1.0
        for result in self.results:
            if ticker == result.company.ticker:
                score = float(result)
                break

        return score

    def _run(self, companies: list[Company]) -> None:
        for company in companies:
            successes = []
            scores = []
            descriptions = []
            self.task_ticker = str(company)
            for filter in self.scripts:
                try:
                    interpreter = Interpreter(company, filter)
                    successes += [interpreter.run()]
                    scores += [interpreter.score]
                    descriptions += [interpreter.description]
                except SyntaxError as e:
                    self.task_state = str(e)
                    _logger.error(f'{__name__}: SyntaxError: {self.task_state}')
                    break
                except RuntimeError as e:
                    self.task_state = str(e)
                    _logger.error(f'{__name__}: RuntimeError: {self.task_state}')
                    break
                except Exception as e:
                    self.task_state = str(e)
                    _logger.error(f'{__name__}: Exception: {self.task_state} for {company}')
                    break

            if self.task_state == 'None':
                self.task_completed += 1

                head_tail = os.path.split(self.screen)
                head, sep, tail = head_tail[1].partition('.')
                price = store.get_last_price(company.ticker)
                self.results += [Result(company, head, successes, scores, descriptions, price)]
                if (bool(self.results[-1])):
                    self.task_success += 1
            else:
                self.task_completed = self.task_total
                self.results = []
                self.valids = []
                break

    def _load(self, script: str, init: str = '') -> bool:
        self.scripts = []
        if os.path.exists(script):
            try:
                with open(script) as f:
                    self.scripts = json.load(f)
            except:
                self.scripts = []
                _logger.error(f'{__name__}: File format error')
            else:
                self._add_init_script(init)
        else:
            _logger.error(f'{__name__}: File "{script}" not found')

        return bool(self.scripts)

    def _open(self) -> bool:
        tickers = []

        if self.type == 'every':
            tickers = store.get_tickers('every')
        elif self.type == 'exchange':
            tickers = store.get_exchange_tickers(self.table)
        elif self.type == 'index':
            tickers = store.get_index_tickers(self.table)
        else:
            tickers = [self.table]

        if len(tickers) > 0:
            try:
                self.companies = [Company(ticker, self.days, backtest=self.backtest, live=self.live) for ticker in tickers]
            except ValueError as e:
                _logger.warning(f'{__name__}: Invalid ticker: {e}')

            if len(self.companies) > 1:
                _logger.info(f'{__name__}: Opened {len(self.companies)} symbols from {self.table} table')
            else:
                _logger.info(f'{__name__}: Opened symbol {self.table}')
        else:
            _logger.warning(f'{__name__}: No symbols available')

        return len(self.companies) > 0

    def _add_init_script(self, script: str) -> bool:
        if not script:
            pass
        elif os.path.exists(script):
            try:
                with open(script) as f:
                    self.scripts += json.load(f)
            except:
                self.scripts = []
                _logger.error(f'{__name__}: File format error')
        else:
            _logger.error(f'{__name__}: File "{script}" not found')

        return bool(self.scripts)

    def _save_results(self) -> None:
        if self.results:
            filename = self._cache_filename()

            with open(filename, 'wb') as f:
                try:
                    pickle.dump(self.results, f, protocol=pickle.HIGHEST_PROTOCOL)  # TODO Understand why dump() sends LF's to console
                except Exception as e:
                    _logger.error(f'{__name__}: Exception for pickle dump: {str(e)}')

            self.cache_available = True

    def _load_results(self) -> bool:
        filename = self._cache_filename()

        cached = False
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                try:
                    self.results = pickle.load(f)
                except Exception as e:
                    _logger.error(f'{__name__}: Exception for pickle load: {str(e)}')
                else:
                    cached = True

        return cached

    def _cache_filename(self) -> str:
        date_time = dt.datetime.now().strftime(ui.DATE_FORMAT)
        head_tail = os.path.split(self.screen)
        head, sep, tail = head_tail[1].partition('.')
        filename = f'{CACHE_BASEPATH}/{date_time}_{self.table.lower()}_{head.lower()}.{CACHE_SUFFIX}'

        return filename


def summarize(results: list[Result]) -> pd.DataFrame:
    summary = pd.DataFrame()

    items = [{
        'ticker': result.company.ticker,
        'valid': bool(result),
        'score': float(result),
        'company': result.company.information['name'],
        'sector': result.company.information['sector'],
        'screen': result.screen.title(),
        'price_last': result.price_last,
        'price_current': result.price_current,
        'backtest_success': result.backtest_success,
    } for result in results]

    if items:
        summary = pd.DataFrame(items)
        summary.index += 1 # Use 1-based index

    return summary

def group_duplicates(results: list[Result]) -> pd.DataFrame:
    items = pd.DataFrame()

    summary = summarize(results)
    dups = summary.duplicated(subset=['ticker'], keep=False)
    duplicated = summary[dups]

    if not duplicated.empty:
        items = duplicated.groupby(['ticker'], sort=False).first()
        items['ticker'] = items.index
        items.index = range(1, len(items)+1)

    return items


if __name__ == '__main__':
    import logging
    logger.get_logger(logging.INFO)

    s = Screener('SP500', 'bulltrend')
    s.run_script()
