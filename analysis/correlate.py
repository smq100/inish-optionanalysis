import datetime as dt

import pandas as pd

from base import Threaded
from data import store as store
from utils import cache, logger, ui

_logger = logger.get_logger()


CORRELATION_CUTOFF = 0.85
CACHE_TYPE = 'cor'


class Correlate(Threaded):
    def __init__(self, tickers: list[str], name: str, days: int = 365):
        if tickers is None:
            raise ValueError('Invalid list of tickers')
        if not tickers:
            raise ValueError('Invalid list of tickers')

        self.tickers = tickers
        self.name = name
        self.results: pd.DataFrame = pd.DataFrame()
        self.filtered: pd.DataFrame = pd.DataFrame()
        self.days: int = days
        self.cache_available = False
        self.cache_date: str = dt.datetime.now().strftime(ui.DATE_FORMAT_YMD)
        self.cache_today_only = cache.CACHE_TODAY_ONLY
        self.cache_available = cache.exists(self.name, CACHE_TYPE, today_only=self.cache_today_only)

    @Threaded.threaded
    def compute(self) -> None:
        self.results = pd.DataFrame()
        combined_df = pd.DataFrame()
        self.task_total = len(self.tickers)

        if self.cache_available:
            combined_df, self.cache_date = cache.load(self.name, CACHE_TYPE, today_only=self.cache_today_only)
        else:
            self.task_state = 'Fetching'
            for ticker in self.tickers:
                self.task_ticker = ticker
                df = store.get_history(ticker, self.days)
                if not df.empty:
                    df = df.set_index('date')
                    df = df.rename(columns={'close': ticker})
                    df = df.drop(['high', 'low', 'open', 'volume'], axis=1)

                    if combined_df.empty:
                        combined_df = df
                    else:
                        combined_df = pd.concat([combined_df, df], axis=1)

                self.task_completed += 1

            if not combined_df.empty:
                cache.dump(combined_df, self.name, CACHE_TYPE)

        if not combined_df.empty:
            self.task_state = 'Correlating'
            self.results = combined_df.fillna(combined_df.mean())
            self.results = combined_df.corr()
            self.task_object = self.results

        self.task_state = 'Done'

    @Threaded.threaded
    def filter(self, sublist: list[str]=[]) -> None:
        self.filtered = pd.DataFrame()

        all_df = pd.DataFrame()
        all = []
        if not self.results.empty:
            if sublist:
                tickers = [ticker for ticker in self.results if ticker in sublist]
            else:
                tickers = [ticker for ticker in self.results if ticker in self.results]

            self.task_total = len(tickers)
            self.task_state = 'Filtering'

            correlation_generator = (self.get_ticker_correlation(ticker) for ticker in tickers)
            for df in correlation_generator:
                self.task_ticker = df.index.name
                for s in df.itertuples():
                    # s = (ticker1, ticker2, correlation)
                    # Arrange the symbol names so we can more easily remove duplicates
                    if df.index.name < s[1]:
                        t = (df.index.name, s[1])
                    else:
                        t = (s[1], df.index.name)

                    # Add if relevant and not already in list
                    if s[2] < CORRELATION_CUTOFF:
                        pass
                    elif t not in all:
                        all.append(t)
                        new = pd.Series({'ticker1':t[0], 'ticker2':t[1], 'correlation':s[2]}).to_frame().T
                        all_df = pd.concat([all_df, new])

                self.task_completed += 1

            all_df = all_df.sort_values(['correlation'], ascending=False)
            self.filtered = all_df.reset_index(drop=True)

        self.task_state = 'Done'

    def get_ticker_correlation(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        df = pd.DataFrame()

        series = pd.Series(dtype=float)
        if not self.results.empty:
            if ticker in self.results.index:
                series = self.results[ticker].sort_values(ascending=False)
                series = series.drop(ticker) # Drop own entry (corr = 1.0)
            else:
                _logger.warning(f'Invalid ticker {ticker}')
        else:
            _logger.warning('Must first compute correlation')

        df = pd.DataFrame({'ticker': series.index, 'value': series.values})
        df.index.name = ticker

        return df


if __name__ == '__main__':
    import logging
    import time
    logger.get_logger(logging.INFO)

    symbols = store.get_tickers('nyse')
    c = Correlate(symbols, 'nyse')

    tic = time.perf_counter()
    c.compute()
    tickers = ['AR', 'EQT', 'OXY', 'HRB', 'MPC', 'RRC', 'VLO', 'XOM', 'PBR', 'EQNR',]
    c.filter(tickers)
    toc = time.perf_counter()
    print(c.results)
    print(c.filtered)
    print(f'Time={toc-tic:.2f}')
