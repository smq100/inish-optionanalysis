import os
import json
import pickle
import random
from datetime import datetime as dt
from concurrent import futures

import numpy as np

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


class Result:
    def __init__(self, company: Company, success: list[bool], score: list[float], results: list[str]):
        self.company = company
        self.success = success
        self.score = score
        self.results = results
        self.backtest_success = False
        self.price_last = 0.0
        self.price_current = 0.0

    def __repr__(self):
        return f'<Result ({self.company.ticker})>'

    def __str__(self):
        return self.company.ticker

    def __bool__(self):
        return all(self.success)

    def __float__(self):
        return float(sum(self.score)) / len(self.score) if len(self.score) > 0 else 0.0


class Screener(Threaded):
    def __init__(self, table: str, screen: str, days: int = 365, end: int = 0, live: bool = False):
        super().__init__()

        self.table = table.upper()
        self.screen = screen
        self.screen_init = f'{SCREEN_BASEPATH}{SCREEN_INIT_NAME}.{SCREEN_SUFFIX}'
        self.cache_available = False
        self.cache_used = False

        if self.table == 'ALL':
            self.type = 'all'
        elif store.is_exchange(self.table):
            self.type = 'exchange'
        elif store.is_index(self.table):
            self.type = 'index'
        elif store.is_ticker(table):
            self.type = 'symbol'
        else:
            self.type = ''
            raise ValueError(f'Table not found: {self.table}')

        if not screen:
            raise ValueError(f'Screen not specified')

        if days < 30:
            raise ValueError('Invalid number of days')

        if end < 0:
            raise ValueError('Invalid "end" days')

        self.days = days
        self.end = end
        self.live = live if store.is_database_connected() else True
        self.scripts: list[dict] = []
        self.companies: list[Company] = []
        self.results: list[Result] = []
        self.valids: list[Result] = []
        self._concurrency = 10

        if self._load(screen, init=self.screen_init):
            self._open()
            self.cache_available = self._load_cache()
        else:
            raise ValueError(f'Script not found or invalid format: {screen}')

    def __repr__(self):
        return f'<Screener ({self.table})>'

    def __str__(self):
        return f'{self.table}/{self.screen}'

    @Threaded.threaded
    def run_script(self, ignore_cache: bool = False, dump_cache: bool = True) -> None:
        self.task_total = len(self.companies)

        if self.cache_available and not ignore_cache:
            self.valids = [result for result in self.results if result]
            self.valids = sorted(self.valids, reverse=True, key=lambda r: float(r))
            self.task_completed = self.task_total
            self.task_success = len(self.valids)
            self.task_error = 'Done'
            self.cache_used = True
            _logger.info(f'{__name__}: Using cached results')
        elif self.task_total == 0:
            self.results = []
            self.valids = []
            self.task_completed = self.task_total
            self.task_error = 'No symbols'
            _logger.warning(f'{__name__}: {self.task_error}')
        elif len(self.scripts) == 0:
            self.results = []
            self.valids = []
            self.task_completed = self.task_total
            self.task_error = 'Illegal script'
            _logger.warning(f'{__name__}: {self.task_error}')
        else:
            self.results = []
            self.valids = []
            self.task_error = 'None'
            self._concurrency = 10 if len(self.companies) > 10 else 1

            if self.task_total > 1:
                _logger.info(f'{__name__}: Screening {self.task_total} symbols from {self.table} table (days={self.days}, end={self.end})')
            else:
                _logger.info(f'{__name__}: Screening {self.table} (days={self.days}, end={self.end})')

            # Randomize and split up the lists
            random.shuffle(self.companies)
            companies = np.array_split(self.companies, self._concurrency)
            companies = [i for i in companies if i is not None]

            with futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
                self.task_futures = [executor.submit(self._run, list) for list in companies]

                for future in futures.as_completed(self.task_futures):
                    _logger.info(f'{__name__}: Thread completed: {future.result()}.')

            self.valids = [result for result in self.results if result]
            self.valids = sorted(self.valids, reverse=True, key=lambda r: float(r))

            if dump_cache:
                self._dump_cache()

            self.task_error = 'Done'

    def _run(self, companies: list[Company]) -> None:
        for ticker in companies:
            success = []
            score = []
            result = []
            self.task_ticker = str(ticker)
            for filter in self.scripts:
                try:
                    interpreter = Interpreter(ticker, filter)
                    success += [interpreter.run()]
                    score += [interpreter.score]
                    result += [interpreter.result]
                except SyntaxError as e:
                    self.task_error = str(e)
                    _logger.error(f'{__name__}: SyntaxError: {self.task_error}')
                    break
                except RuntimeError as e:
                    self.task_error = str(e)
                    _logger.error(f'{__name__}: RuntimeError: {self.task_error}')
                    break
                except Exception as e:
                    self.task_error = str(e)
                    _logger.error(f'{__name__}: Exception: {self.task_error} for {ticker}')
                    break

            if self.task_error == 'None':
                self.task_completed += 1
                self.results += [Result(ticker, success, score, result)]
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
                if init:
                    self._add_init_script(init)
        else:
            _logger.error(f'{__name__}: File "{script}" not found')

        return bool(self.scripts)

    def _open(self) -> bool:
        tickers = []

        if self.type == 'all':
            tickers = store.get_tickers()
        elif self.type == 'exchange':
            tickers = store.get_exchange_tickers(self.table)
        elif self.type == 'index':
            tickers = store.get_index_tickers(self.table)
        else:
            tickers = [self.table]

        if len(tickers) > 0:
            try:
                self.companies = [Company(s, self.days, end=self.end, live=self.live) for s in tickers]
            except ValueError as e:
                _logger.warning(f'{__name__}: Invalid ticker {s}')

            if len(self.companies) > 1:
                _logger.info(f'{__name__}: Opened {len(self.companies)} symbols from {self.table} table')
            else:
                _logger.info(f'{__name__}: Opened symbol {self.table}')
        else:
            _logger.warning(f'{__name__}: No symbols available')

        return len(self.companies) > 0

    def _add_init_script(self, script: str) -> bool:
        if os.path.exists(script):
            try:
                with open(script) as f:
                    self.scripts += json.load(f)
            except:
                self.scripts = []
                _logger.error(f'{__name__}: File format error')
        else:
            _logger.error(f'{__name__}: File "{script}" not found')

        return bool(self.scripts)

    def _dump_cache(self) -> None:
        if self.results:
            filename = self._build_cache_filename()

            with open(filename, 'wb') as f:
                pickle.dump(self.results, f)

            self.cache_available = True

    def _load_cache(self) -> bool:
        filename = self._build_cache_filename()

        cached = False
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                self.results = pickle.load(f)
                cached = True

        return cached

    def _build_cache_filename(self) -> str:
        date_time = dt.now().strftime('%Y-%m-%d')
        head_tail = os.path.split(self.screen)
        head, sep, tail = head_tail[1].partition('.')
        filename = f'{CACHE_BASEPATH}/{date_time}_{self.table}_{head.upper()}.{CACHE_SUFFIX}'

        return filename


if __name__ == '__main__':
    import logging

    ui.get_logger(logging.DEBUG)

    s = Screener('DOW')
    s._load('/Users/steve/Documents/Source Code/Personal/OptionAnalysis/screener/screens/test.screen')
    # s.run_script()
