import pandas as pd

from base import Threaded
from data import store as store
from utils import logger

_logger = logger.get_logger()


class Correlate(Threaded):
    def __init__(self, tickers: list[str], days: int = 365):
        if tickers is None:
            raise ValueError('Invalid list of tickers')
        if not tickers:
            raise ValueError('Invalid list of tickers')

        self.tickers = tickers
        self.correlation: pd.DataFrame = pd.DataFrame()
        self.days: int = days

    @Threaded.threaded
    def compute(self) -> None:
        self.correlation = pd.DataFrame()
        combined_df = pd.DataFrame()
        self.task_total = len(self.tickers)
        self.task_state = 'None'

        for ticker in self.tickers:
            self.task_ticker = ticker

            df = store.get_history(ticker, self.days)
            if not df.empty:
                df.set_index('date', inplace=True)
                df.rename(columns={'close': ticker}, inplace=True)
                df.drop(['high', 'low', 'open', 'volume'], axis=1, inplace=True)

                if combined_df.empty:
                    combined_df = df
                else:
                    combined_df = pd.concat([combined_df, df], axis=1)

            self.task_completed += 1

        if not combined_df.empty:
            self.correlation = combined_df.fillna(combined_df.mean())
            self.correlation = combined_df.corr()

            self.task_object = self.correlation
            self.task_success += 1

        self.task_state = 'Done'

    def get_correlations(self, sublist: list[str]=[]) -> pd.DataFrame:
        all_df = pd.DataFrame()
        all = []
        if not self.correlation.empty:
            if sublist:
                coors_gen = (self.get_ticker_correlation(ticker) for ticker in self.correlation if ticker in sublist)
            else:
                coors_gen = (self.get_ticker_correlation(ticker) for ticker in self.correlation)

            for df in coors_gen:
                for s in df.itertuples():
                    # Arrange the symbol names so we can more easily remove duplicates
                    if df.index.name < s[1]:
                        t = (df.index.name, s[1])
                    else:
                        t = (s[1], df.index.name)

                    if t not in all:
                        all += [t]
                        new = pd.Series({'ticker1':t[0], 'ticker2':t[1], 'correlation':s[2]}).to_frame().T
                        all_df = pd.concat([all_df, new])

            all_df.reset_index(drop=True, inplace=True)

        return all_df

    def get_ticker_correlation(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        df = pd.DataFrame()

        series = pd.Series(dtype=float)
        if not self.correlation.empty:
            if ticker in self.correlation.index:
                series = self.correlation[ticker].sort_values()
                series.drop(ticker, inplace=True)  # Drop own entry (coor = 1.0)
            else:
                _logger.warning(f'{__name__}: Invalid ticker {ticker}')
        else:
            _logger.warning(f'{__name__}: Must first compute correlation')

        df = pd.DataFrame({'ticker': series.index, 'value': series.values})
        df.index.name = ticker

        return df


if __name__ == '__main__':
    symbols = store.get_tickers('DOW')
    c = Correlate(symbols)
    c.compute()
    # print(c.correlation)
    tickers = ['CRM', 'DIS']
    all = c.get_correlations(tickers)
    print(all)