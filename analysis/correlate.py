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

    @Threaded.threaded
    def correlate(self):
        main_df = pd.DataFrame()
        self.task_total = len(self.tickers)
        self.task_error = 'None'

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
            self.task_object = main_df.fillna(main_df.mean()).corr()

        self.task_error = 'Done'

if __name__ == '__main__':
    symbols = store.get_symbols('DOW')
    c = Correlate()
    df = c.correlate(symbols)
    print(df)
