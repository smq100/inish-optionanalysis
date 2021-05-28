import pandas as pd

from base import Threaded
from data import store as store
from utils import utils as utils

_logger = utils.get_logger()


class Correlate(Threaded):
    def __init__(self, tickers):
        if tickers is None:
            raise ValueError('Invalid list of tickers')
        if not tickers:
            raise ValueError('Invalid list of tickers')

        self.tickers = tickers
        self.correlation = None

    @Threaded.threaded
    def compute_correlation(self):
        main_df = pd.DataFrame()
        self.task_total = len(self.tickers)
        self.task_error = 'None'
        self.correlation = None

        for ticker in self.tickers:
            self.task_symbol = ticker
            self.task_completed += 1

            df = store.get_history(ticker, 365)
            if not df.empty:
                df.set_index('date', inplace=True)
                df.rename(columns={'close':ticker}, inplace=True)
                df.drop(['high', 'low', 'open', 'volume'], 1, inplace=True)

                if main_df.empty:
                    main_df = df
                else:
                    main_df = main_df.join(df, how='outer')

        if not main_df.empty:
            self.correlation = main_df.fillna(main_df.mean()).corr()
            self.task_object = self.correlation

        self.task_error = 'Done'

    def get_sorted_coorelations(self, count, best):
        all = self.get_all_coorelations()
        if all is not None:
            all.sort(key=lambda x: x[2], reverse=best)

        return all[:count]

    def get_all_coorelations(self):
        all = []
        if self.correlation is not None and not self.correlation.empty:
            coors = (self.get_symbol_coorelation(sym) for sym in self.correlation)
            for sym in coors:
                for s in sym.iteritems():
                    # Arrange the symbol names so we can more easily remove duplicaates
                    if sym.name < tuple(s)[0]:
                        t = (sym.name, tuple(s)[0], tuple(s)[1])
                    else:
                        t = (tuple(s)[0], sym.name, tuple(s)[1])

                    if t not in all:
                        all += [t]

        return all

    def get_symbol_coorelation(self, ticker):
        df = pd.DataFrame()
        ticker = ticker.upper()

        if self.correlation is not None and not self.correlation.empty:
            if ticker in self.correlation.index:
                df = self.correlation[ticker].sort_values()
                df.drop(ticker, inplace=True) # Drop own entry (coor = 1.0)
            else:
                _logger.warning(f'{__name__}: Invalid ticker {ticker}')
        else:
                _logger.warning(f'{__name__}: No dataframe')

        return df


if __name__ == '__main__':
    symbols = store.get_symbols('DOW')
    c = Correlate()
    df = c.compute_correlation(symbols)
    print(df)
