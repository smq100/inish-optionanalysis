import datetime as dt
import random
from concurrent import futures

import numpy as np
import pandas as pd

from base import Threaded
from data import store as store
from utils import cache, logger, ui

_logger = logger.get_logger()

CACHE_TYPE = 'gap'
THRESHOLD = 0.01

MINPRICE = 1.0
MINVOLUME = 500e3

class Gap(Threaded):
    def __init__(self, tickers: list[str], name: str, days: int = 300, threshold: float = THRESHOLD):
        self.tickers: list[str] = tickers
        self.days: int = days
        self.threshold: float = threshold
        self.results: list[pd.DataFrame]
        self.analysis: pd.DataFrame = pd.DataFrame()
        self.concurrency: int = 10
        self.cache_name: str = name
        self.cache_available: bool = False
        self.cache_used: bool = False
        self.cache_date: str = dt.datetime.now().strftime(ui.DATE_FORMAT)
        self.cache_today_only: bool = cache.CACHE_TODAY_ONLY

        for ticker in tickers:
            if not store.is_ticker(ticker):
                raise ValueError(f'{__name__}: Not a valid ticker: {ticker}')

        self.cache_available = cache.exists(name, CACHE_TYPE, today_only=self.cache_today_only)
        if self.cache_available:
            self.results, self.cache_date = cache.load(name, CACHE_TYPE, today_only=self.cache_today_only)
            _logger.info(f'{__name__}: Cached results from {self.cache_date} available')

    @Threaded.threaded
    def calculate(self, use_cache: bool = True) -> None:
        if not self.tickers:
            assert ValueError('No valid tickers specified')

        _logger.info(f'{__name__}: Calculating {len(self.tickers)} ticker(s)')

        if use_cache and self.cache_available:
            self.cache_used = True
            _logger.info(f'{__name__}: Using cached results.')
        else:
            self.cache_used = False
            self.task_total = len(self.tickers)
            self.task_state = 'None'
            self.results = []
            self.analysis = pd.DataFrame()

            # Break up the tickers and run concurrently if a large list, otherwise just run the single list
            if len(self.tickers) > 100:
                _logger.info(f'{__name__}: Running with thread pool')

                random.shuffle(self.tickers)
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

            if use_cache and self.results:
                cache.dump(self.results, self.cache_name, CACHE_TYPE)
                _logger.info(f'{__name__}: Results from {self.cache_name} saved to cache')

        self.task_state = 'Done'

    def analyze(self) -> None:
        self.analysis = pd.DataFrame()

        analysis = []
        for result in self.results:
            if result.iloc[-1]['unfilled'] > 0.0:
                size = abs(result.iloc[-1]['gap']) / result.iloc[-1]['start']
                analysis.append({
                    'ticker': result.index.name,
                    'start': result.iloc[-1]['start'],
                    'gap': result.iloc[-1]['gap'],
                    'unfilled': result.iloc[-1]['unfilled'],
                    'relative': size})

        if analysis:
            df = pd.DataFrame(analysis)
            df = df.sort_values(['relative'], ascending=False)
            self.analysis = df.reset_index(drop=True)

        _logger.info(f'{__name__}: Analyzing {len(self.results)} result(s)')

    def _run(self, tickers: list[str]) -> None:
        for ticker in tickers:
            self.task_ticker = ticker
            history = store.get_history(ticker, days=self.days)

            if history.iloc[-10:]['volume'].mean() < MINVOLUME:
                pass # Ignore low volume tickers
            elif history.iloc[0]['close'] < MINPRICE:
                pass # Ignore low price tickers
            else:
                history = history.drop(['volume', 'open'], axis=1)
                history['up'] = history['low'] - history['high'].shift(1)
                history['dn'] = history['low'].shift(1) - history['high']

                # Find relevant gap ups
                up = history[history['up'] > (history['close'] * self.threshold)].copy()
                up = up[up['close'] > MINPRICE]
                for result in up.itertuples():
                    df = history.loc[history['date'] >= result.date]
                    high = history.iloc[result.Index-1]['high']
                    low = history.iloc[result.Index]['low']
                    min_low = df['low'].min()
                    up.loc[result.Index, 'index'] = result.Index
                    up.loc[result.Index, 'start'] = high
                    up.loc[result.Index, 'gap'] = low - high
                    if min_low > high:
                        up.loc[result.Index, 'unfilled'] = min_low - high
                    else:
                        up.loc[result.Index, 'unfilled'] = 0.0

                # Find relevant gap downs
                dn = history[history['dn'] > (history['close'] * self.threshold)].copy()
                dn = dn[dn['close'] > MINPRICE]
                for result in dn.itertuples():
                    df = history.loc[history['date'] >= result.date]
                    low = history.iloc[result.Index-1]['low']
                    high = history.iloc[result.Index]['high']
                    max_high = df['high'].max()
                    dn.loc[result.Index, 'index'] = result.Index
                    dn.loc[result.Index, 'start'] = low
                    dn.loc[result.Index, 'gap'] = high - low
                    if low > max_high:
                        dn.loc[result.Index, 'unfilled'] = low - max_high
                    else:
                        dn.loc[result.Index, 'unfilled'] = 0.0

                # Clean and combine the results
                results = pd.concat([up, dn]).sort_index().reset_index(drop=True)
                if not results.empty:
                    results = results.drop(['high', 'low', 'close'], axis=1)
                    results = results.drop(['up', 'dn'], axis=1)
                    results.index.name = ticker.upper()
                    self.results.append(results)

            self.task_completed += 1

if __name__ == '__main__':
    import logging
    import sys

    from tabulate import tabulate

    from utils import logger

    # logger.get_logger(logging.INFO)

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'NFLX'

    gap = Gap([ticker], 'test', threshold=0.01)
    gap.calculate(use_cache=False)

    if not gap.results:
        pass
    elif not gap.results[0].empty:
        headers = ui.format_headers(gap.results[0].columns, case='lower')
        print(tabulate(gap.results[0], headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
    else:
        print('No gaps')

    gap.analyze()
