import datetime as dt

import pandas as pd

import etrade.auth as auth
from etrade.options import Options


def get_option_expiry(ticker: str) -> tuple[str]:
    if auth.Session is None:
        raise ValueError('Must authorize E*Trade session')

    options = Options()
    expiry_data = options.expiry(ticker)
    expiry = tuple([f'{item.date:%Y-%m-%d}' for item in expiry_data.itertuples()])

    return expiry


def get_option_chain(ticker: str, expiry: dt.datetime) -> pd.DataFrame:
    if auth.Session is None:
        raise ValueError('Must authorize E*Trade session')

    chain = pd.DataFrame()
    options = Options()

    year = expiry.year
    month = expiry.month
    chain = options.chain(ticker, month, year)

    rename = {
        'osiKey': 'contractSymbol',
        'strikePrice': 'strike'
    }
    chain = chain.rename(rename, axis=1)

    order = [
        'contractSymbol',
        'symbol',
        'type',
        'strike',
        'lastPrice',
        'inTheMoney',
        'impliedVolatility',
        'volume',
    ]
    chain = chain.reindex(columns=order)

    return chain


if __name__ == '__main__':
    pass
