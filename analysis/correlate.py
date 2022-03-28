import pandas as pd

from base import Threaded
from data import store as store
from utils import ui, logger

_logger = logger.get_logger()


class Correlate(Threaded):
    def __init__(self, tickers: list[str]):
        if tickers is None:
            raise ValueError('Invalid list of tickers')
        if not tickers:
            raise ValueError('Invalid list of tickers')

        self.tickers = tickers
        self.correlation: pd.DataFrame = None

    @Threaded.threaded
    def compute_correlation(self) -> None:
        main_df = pd.DataFrame()
        self.task_total = len(self.tickers)
        self.task_state = 'None'
        self.correlation = None

        for ticker in self.tickers:
            self.task_ticker = ticker

            df = store.get_history(ticker, 365)
            if not df.empty:
                df.set_index('date', inplace=True)
                df.rename(columns={'close': ticker}, inplace=True)
                df.drop(['high', 'low', 'open', 'volume'], axis=1, inplace=True)

                if main_df.empty:
                    main_df = df
                else:
                    main_df = main_df.join(df, how='outer')

            self.task_completed += 1

        if not main_df.empty:
            self.correlation = main_df.fillna(main_df.mean())
            self.correlation = main_df.corr()
            self.task_object = self.correlation
            self.task_success += 1

        self.task_state = 'Done'

    def get_sorted_coorelations(self, count: int, best: bool) -> list[tuple[str, str, float]]:
        all = self.get_all_coorelations()
        if all is not None:
            all.sort(key=lambda sym: sym[2], reverse=best)

        return all[:count]

    def get_all_coorelations(self) -> list[tuple[str, str, float]]:
        all = []
        if self.correlation is not None and not self.correlation.empty:
            coors = (self.get_ticker_coorelation(sym) for sym in self.correlation)
            for sym in coors:
                for s in sym.iteritems():
                    # Arrange the symbol names so we can more easily remove duplicates
                    if sym.name < tuple(s)[0]:
                        t = (sym.name, tuple(s)[0], tuple(s)[1])
                    else:
                        t = (tuple(s)[0], sym.name, tuple(s)[1])

                    if t not in all:
                        all += [t]

        return all

    def get_ticker_coorelation(self, ticker: str) -> pd.DataFrame:
        series = pd.Series
        ticker = ticker.upper()

        if self.correlation is not None and not self.correlation.empty:
            if ticker in self.correlation.index:
                series = self.correlation[ticker].sort_values()
                series.drop(ticker, inplace=True)  # Drop own entry (coor = 1.0)
            else:
                _logger.warning(f'{__name__}: Invalid ticker {ticker}')
        else:
            _logger.warning(f'{__name__}: No dataframe')

        return pd.DataFrame({'ticker': series.index, 'value': series.values})


if __name__ == '__main__':
    symbols = store.get_tickers('DOW')
    c = Correlate(symbols)
    df = c.compute_correlation()
    print(df)
