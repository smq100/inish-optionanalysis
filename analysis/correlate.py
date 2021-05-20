from numpy import empty
import pandas as pd

from data import store as store
from utils import utils as utils

_logger = utils.get_logger()


def correlate(tickers):
    main_df = pd.DataFrame()

    for ticker in tickers:
        df = store.get_history(ticker, 365)
        df.set_index('date', inplace=True)
        df.rename(columns={'close':ticker}, inplace=True)
        df.drop(['high', 'low', 'open', 'volume'], 1, inplace=True)

        if main_df is empty:
            main_df = df
        else:
            main_df = main_df.join(df, how='outer')

    main_df.fillna(0, inplace=True)

    return main_df.corr()

if __name__ == '__main__':
    # from logging import DEBUG
    # logger = u.get_logger(DEBUG)

    symbols = store.get_symbols('DOW')
    df = correlate(symbols)

    print(df)
