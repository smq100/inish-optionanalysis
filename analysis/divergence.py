import random
import datetime as dt
from concurrent import futures

import pandas as pd
import numpy as np
from ta import trend
from sklearn.preprocessing import MinMaxScaler

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, cache, logger


_logger = logger.get_logger()

CACHE_TYPE = 'div'


class Divergence(Threaded):
    def __init__(self, tickers: list[str], name: str, window: int = 15, days: int = 100):
        self.tickers: list[str] = tickers
        self.window: int = window
        self.days: int = days
        self.results: list[pd.DataFrame] = []
        self.analysis: pd.DataFrame = pd.DataFrame()
        self.type: str = 'rsi'
        self.interval: int = 14
        self.periods: int = days // 50
        self.streak: int = 5
        self.concurrency: int = 10
        self.scaled: bool = True
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
    def calculate(self, use_cache: bool = True, scaled: bool = True) -> None:
        if not self.tickers:
            assert ValueError('No valid tickers specified')

        _logger.info(f'{__name__}: Calculating {len(self.tickers)} ticker(s)')

        if use_cache and self.cache_available:
            self.cache_used = True
            _logger.info(f'{__name__}: Using cached results. Scaled={scaled}')
        else:
            self.scaled = scaled
            self.task_total = len(self.tickers)
            self.task_state = 'None'
            self.results = []

            # Break up the tickers and run concurrently if a large list, otherwise just run the single list
            random.shuffle(self.tickers)
            if len(self.tickers) > 100:
                _logger.info(f'{__name__}: Running with thread pool. Scaled={scaled}')

                tickers: list[np.ndarray] = np.array_split(self.tickers, self.concurrency)
                tickers = [i.tolist() for i in tickers]

                with futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                    self.task_futures = [executor.submit(self._run, ticker_list) for ticker_list in tickers]

                    for future in futures.as_completed(self.task_futures):
                        _logger.info(f'{__name__}: Thread completed: {future.result()}')
            else:
                _logger.info(f'{__name__}: Running without thread pool. Scaled={scaled}')

                use_cache = False
                self._run(self.tickers)

            if use_cache:
                cache.dump(self.results, self.cache_name, CACHE_TYPE)
                _logger.info(f'{__name__}: Results from {self.cache_name} saved to cache')

        self.task_state = 'Done'

    def analyze(self, streak: int = 5) -> None:
        if not self.results:
            assert ValueError('No valid results specified')

        _logger.info(f'{__name__}: Analyzing {len(self.results)} result(s)')

        self.streak = streak
        self.analysis = pd.DataFrame()
        for result in self.results:
            idx = result[::-1]['streak'].idxmax()  # Index of most recent largest streak
            date = result.iloc[idx]['date']
            max = result.iloc[idx]['streak']
            if max >= streak:
                data = [[result.index.name, date, max]]
                df = pd.DataFrame(data, columns=['ticker', 'date', 'streak'])
                self.analysis = pd.concat([self.analysis, df], ignore_index=True)

        if len(self.analysis) > 0:
            self.analysis = self.analysis.reset_index()
            self.analysis = self.analysis.sort_values(by=['streak'], ascending=False)

    def _run(self, tickers: list[str]) -> None:
        for ticker in tickers:
            ta = Technical(ticker, None, self.days)
            history = ta.history
            result = pd.DataFrame()

            # Use scaled & normalized values for comparison
            scaler = MinMaxScaler(feature_range=(0, 1))

            # Base data
            dates = history['date'][self.interval:].reset_index(drop=True)
            price = history['close'][self.interval:].reset_index(drop=True)

            if not history.empty and not price.empty:
                self.task_ticker = ticker

                # Calculate 0-1 scaled series of day-to-day rsi differences
                price.name = 'price'
                price_sma = trend.sma_indicator(price, window=self.window, fillna=True).reset_index(drop=True)
                price_sma.name = 'price_sma'
                price_sma_diff = price_sma.diff(periods=self.periods).fillna(0.0)
                price_sma_diff.name = 'price_sma_diff'
                scaled = scaler.fit_transform(price_sma.values.reshape(-1, 1))
                scaled = [value[0] for value in scaled]
                price_sma_scaled = pd.Series(scaled, name='price_sma_scaled')
                price_sma_scaled_diff = price_sma_scaled.diff(periods=self.periods).fillna(0.0)
                price_sma_scaled_diff.name = 'price_sma_scaled_diff'

                # Calculate 0-1 scaled series of day-to-day rsi differences
                technical = ta.calc_rsi(self.interval)[self.interval:]
                technical_sma = trend.sma_indicator(technical, window=self.window, fillna=True).reset_index(drop=True)
                technical_sma.name = f'{self.type}_sma'
                technical_sma_diff = technical_sma.diff(periods=self.periods).fillna(0.0)
                technical_sma_diff.name = f'{self.type}_sma_diff'
                scaled = scaler.fit_transform(technical_sma.values.reshape(-1, 1))
                scaled = [value[0] for value in scaled]
                technical_sma_scaled = pd.Series(scaled, name=f'{self.type}_sma_scaled')
                technical_sma_scaled_diff = technical_sma_scaled.diff(periods=self.periods).fillna(0.0)
                technical_sma_scaled_diff.name = f'{self.type}_sma_scaled_diff'

                # Calculate differences in the slopes between prices and RSI's
                if self.scaled:
                    divergence = technical_sma_scaled_diff - price_sma_scaled_diff
                else:
                    divergence = technical_sma_diff - price_sma_diff
                divergence.name = 'diff'

                # Calculate differences in the slopes between prices and RSI's for opposite slopes only
                div = []
                for i in range(len(price_sma_scaled_diff)):
                    p = price_sma_scaled_diff[i] if self.scaled else price_sma_diff[i]
                    t = technical_sma_scaled_diff[i] if self.scaled else technical_sma_diff[i]
                    div += [t - p if p * t < 0.0 else np.NaN]
                divergence_only = pd.Series(div, name='div')

                # Begin overall result dataframe with the dates
                result = dates

                # Price data
                result = pd.concat([result, price], axis=1)
                result = pd.concat([result, price_sma], axis=1)
                result = pd.concat([result, price_sma_diff], axis=1)
                result = pd.concat([result, price_sma_scaled], axis=1)
                result = pd.concat([result, price_sma_scaled_diff], axis=1)

                # Technical data
                tech = technical.reset_index(drop=True)
                result = pd.concat([result, tech], axis=1)
                result = pd.concat([result, technical_sma], axis=1)
                result = pd.concat([result, technical_sma_diff], axis=1)
                result = pd.concat([result, technical_sma_scaled], axis=1)
                result = pd.concat([result, technical_sma_scaled_diff], axis=1)
                result = pd.concat([result, divergence], axis=1)
                result = pd.concat([result, divergence_only], axis=1)

                # Streak data
                analysis = result.loc[:, ('date', 'div')]
                analysis['tmp1'] = analysis['div'].notna() == True
                analysis['tmp2'] = analysis['tmp1'].ne(analysis['tmp1'].shift())
                analysis['tmp3'] = analysis['tmp2'].cumsum()
                analysis['tmp4'] = analysis.groupby('tmp3').cumcount() + 1
                analysis['streak'] = np.where(analysis['tmp1'] == True, analysis['tmp4'], 0)
                result = pd.concat([result, analysis['streak']], axis=1)

                result.index.name = f'{ticker.upper()}'

                if not result.empty:
                    self.results.append(result)

            self.task_completed += 1


if __name__ == '__main__':
    import sys
    from tabulate import tabulate
    from utils import logger

    import logging
    logger.get_logger(logging.INFO)

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'IBM'

    div = Divergence([ticker])
    div.calculate()

    headers = ui.format_headers(div.results[0].columns, case='lower')
    print(tabulate(div.results[0], headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.3f'))

    div.analyze()
