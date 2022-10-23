import random
import datetime as dt
from concurrent import futures

import pandas as pd
import numpy as np

from base import Threaded
from data import store as store
from utils import ui, cache, logger


_logger = logger.get_logger()

CACHE_TYPE = 'gap'


class Gap(Threaded):
    def __init__(self, tickers: list[str], name: str, days: int = 300):
        self.tickers: list[str] = tickers
        self.days: int = days
        self.results: pd.DataFrame()
        self.analysis: pd.DataFrame()
        self.concurrency: int = 10
        self.cache_name: str = name
        self.cache_available: bool = False
        self.cache_used: bool = False
        self.cache_date: str = dt.datetime.now().strftime(ui.DATE_FORMAT)
        self.cache_today_only: bool = cache.CACHE_TODAY_ONLY

        for ticker in tickers:
            if not store.is_ticker(ticker):
                raise ValueError(f'{__name__}: Not a valid ticker: {ticker}')

    @Threaded.threaded
    def calculate(self, use_cache: bool = True, ) -> None:
        if not self.tickers:
            assert ValueError('No valid tickers specified')

        if use_cache and self.cache_available:
            self.cache_used = True
            _logger.info(f'{__name__}: Using cached results.')
        else:
            self.task_total = len(self.tickers)
            self.task_state = 'None'
            self.results = []

            # Break up the tickers and run concurrently if a large list, otherwise just run the single list
            random.shuffle(self.tickers)
            if len(self.tickers) > 100:
                _logger.info(f'{__name__}: Running with thread pool')

                tickers: list[np.ndarray] = np.array_split(self.tickers, self.concurrency)
                tickers = [i.tolist() for i in tickers]

                with futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                    self.task_futures = [executor.submit(self._run, ticker_list) for ticker_list in tickers]

                    for future in futures.as_completed(self.task_futures):
                        _logger.info(f'{__name__}: Thread completed: {future.result()}')
            else:
                _logger.info(f'{__name__}: Running without thread pool')

                use_cache = False
                self._run(self.tickers)

            if use_cache and not self.results:
                cache.dump(self.results, self.cache_name, CACHE_TYPE)
                _logger.info(f'{__name__}: Results from {self.cache_name} saved to cache')

        self.task_state = 'Done'

    def analyze(self) -> None:
        if not self.results:
            assert ValueError('No valid results specified')

    def _run(self, tickers: list[str]) -> None:
        _logger.info(f'{__name__}: Running {len(tickers)} ticker(s)')

        for ticker in tickers:
            self.task_ticker = ticker
            history = store.get_history(ticker, days=self.days)
            self.task_completed += 1


if __name__ == '__main__':
    pass
