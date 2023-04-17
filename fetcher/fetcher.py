import time
import socket
import datetime as dt

import pandas as pd

import data as d
from fetcher import source_yfinance as yf
from fetcher import source_marketdata as md
from fetcher import source_etrade as et
from fetcher import source_quandl as qd
from utils import logger


_logger = logger.get_logger()

THROTTLE_FETCH = 0.05  # Min secs between calls to fetch pricing

_elapsed = 0.0


def is_connected(hostname: str = 'google.com') -> bool:
    try:
        host = socket.gethostbyname(hostname)
        s = socket.create_connection((host, 80), 2)
        s.close()
    except Exception:
        return False
    else:
        return True


_connected = is_connected()


def validate_ticker(ticker: str) -> bool:
    return yf.validate_ticker(ticker)


def get_history_live(ticker: str, days: int = -1) -> pd.DataFrame:
    if not _connected:
        raise ConnectionError('No internet connection')

    global _elapsed

    # Throttle requests to help avoid being cut off by data provider
    while (time.perf_counter() - _elapsed) < THROTTLE_FETCH:
        time.sleep(THROTTLE_FETCH)

    _elapsed = time.perf_counter()

    _logger.info(f'Fetching {ticker} history from {d.ACTIVE_HISTORYDATASOURCE}...')

    if d.ACTIVE_HISTORYDATASOURCE == 'yfinance':
        history = yf.get_history(ticker, days=days)
    elif d.ACTIVE_HISTORYDATASOURCE == 'marketdata':
        history = md.get_history(ticker, days=days)
    elif d.ACTIVE_HISTORYDATASOURCE == 'quandl':
        history = qd.get_history(ticker, days=days)
    else:
        raise ValueError('Invalid data source')

    if history is None:
        history = pd.DataFrame()
        _logger.error(f'\'None\' object for {ticker} (2)')
    elif history.empty:
        _logger.info(f'Empty live history for {ticker}')

    return history


def get_company_live(ticker: str) -> dict:
    company = {}

    c = yf.get_company(ticker)
    if c is not None:
        company = c.info
        company['market_cap'] = c.info.get('market_cap', 0)

    return company


def get_option_expiry(ticker: str) -> tuple[str]:
    if not _connected:
        raise ConnectionError('No internet connection')

    if d.ACTIVE_OPTIONDATASOURCE == 'yfinance':
        expiry = yf.get_option_expiry(ticker)
    elif d.ACTIVE_OPTIONDATASOURCE == 'etrade':
        expiry = et.get_option_expiry_etrade(ticker)
    else:
        raise ValueError('Invalid data source')

    _logger.debug(f'Expiries: {expiry}')

    return expiry


def get_option_chain(ticker: str, expiry: dt.datetime) -> pd.DataFrame:
    if not _connected:
        raise ConnectionError('No internet connection')

    chain = pd.DataFrame()
    if d.ACTIVE_OPTIONDATASOURCE == 'yfinance':
        chain = yf.get_option_chain(ticker, expiry)
    elif d.ACTIVE_OPTIONDATASOURCE == 'etrade':
        chain = et.get_option_chain_etrade(ticker, expiry)
    else:
        raise ValueError('Invalid data source')

    _logger.debug(f'Chain:\n{chain}')

    return chain


def get_ratings(ticker: str) -> list[int]:
    if not _connected:
        raise ConnectionError('No internet connection')

    return yf.get_ratings(ticker)


def get_treasury_rate(ticker: str) -> float:
    if not _connected:
        raise ConnectionError('No internet connection')

    return qd.get_treasury_rate(ticker)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        c = get_history_live(sys.argv[1], days=20)
    else:
        c = get_history_live('AAPL', days=20)

    print(c)