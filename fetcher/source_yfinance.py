'''
yfinance: https://github.com/ranaroussi/yfinance
'''

import time
import datetime as dt

import pandas as pd
import yfinance as yf

import data as d
from utils import ui, logger


THROTTLE_FETCH = 0.05  # Min secs between calls to fetch pricing
THROTTLE_ERROR = 1.00  # Min secs between calls after error
RETRIES = 2            # Number of fetch retries after error


_logger = logger.get_logger()
_last_company: pd.DataFrame = pd.DataFrame()
_last_ticker: str = ''


def validate_ticker(ticker: str) -> bool:
    valid = False

    # YFinance (or Pandas) throws exceptions with bad info (YFinance bug?)
    try:
        _logger.info(f'Fetching Yahoo ticker information for {ticker}...')
        if yf.Ticker(ticker) is not None:
            valid = True
    except Exception:
        valid = False

    return valid


def get_company(ticker: str) -> yf.Ticker:
    global _last_company, _last_ticker

    if ticker == _last_ticker:
        company = _last_company
        _logger.info(f'Using cached company information for {ticker} from Yahoo')
    else:
        company = yf.Ticker(ticker)
        _logger.info(f'Fetched live company information for {ticker} from Yahoo')

    _last_company = company
    _last_ticker = ticker

    return company


def get_history(ticker: str, days: int = -1) -> pd.DataFrame:
    history: pd.DataFrame = pd.DataFrame()
    company = get_company(ticker)

    if company is None:
        _logger.error(f'\'None\' object for {ticker} (1)')
    else:
        if days < 0:
            days = 7300  # 20 years

        if days > 0:
            end = dt.datetime.today()
            start = end - dt.timedelta(days=days)

            for retry in range(RETRIES):
                try:
                    kwargs = {'debug': False}
                    history = company.history(start=start, end=end, interval='1d', timeout=2.0, back_adjust=True, **kwargs)

                    if history is None:
                        history = pd.DataFrame()
                        _logger.warning(f'{d.ACTIVE_HISTORYDATASOURCE} history for {ticker} is None ({retry+1})')
                        time.sleep(THROTTLE_ERROR)
                    elif history.empty:
                        _logger.warning(f'{d.ACTIVE_HISTORYDATASOURCE} history for {ticker} is empty ({retry+1})')
                        time.sleep(THROTTLE_ERROR)
                    elif history.shape[1] == 0:
                        history = pd.DataFrame()
                        _logger.warning(f'{d.ACTIVE_HISTORYDATASOURCE} history for {ticker} has no columns ({retry+1})')
                        time.sleep(THROTTLE_ERROR)
                    else:
                        days = history.shape[0]
                        history = history.reset_index()

                        # Clean some things up and make colums consistent with Postgres column names
                        history.columns = history.columns.str.lower()
                        history = history.drop(['dividends', 'stock splits'], axis=1)
                        history = history.sort_values('date', ascending=True)

                        _logger.info(f'{ticker} Fetched {days} days of live history of {ticker} starting {start:%Y-%m-%d}')
                        break
                except Exception as e:
                    _logger.error(f'Exception: {e}: During attempt {retry+1} to fetch history of {ticker} from {d.ACTIVE_HISTORYDATASOURCE}')
                    history = pd.DataFrame()
                    time.sleep(THROTTLE_ERROR)

    return history


def get_option_expiry(ticker: str) -> tuple[str]:
    expiry = ('',)
    for retry in range(RETRIES):
        company = get_company(ticker)
        if company is not None:
            expiry = company.options
            break
        else:
            _logger.warning(f'Retry {retry} to fetch option expiry for {ticker} using yfinance')
            time.sleep(THROTTLE_ERROR)

    return expiry


def get_option_chain(ticker: str, expiry: dt.datetime) -> pd.DataFrame:
    chain = pd.DataFrame()
    for retry in range(RETRIES):
        company = get_company(ticker)
        if company is not None:
            chain_c = company.option_chain(expiry.strftime(ui.DATE_FORMAT_YMD)).calls
            chain_c['type'] = 'call'
            chain_p = company.option_chain(expiry.strftime(ui.DATE_FORMAT_YMD)).puts
            chain_p['type'] = 'put'
            chain = pd.concat([chain_c, chain_p], axis=0)

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

            break
        else:
            _logger.warning(f'Retry {retry} to fetch option chain for {ticker}')
            time.sleep(THROTTLE_ERROR)

    return chain


if __name__ == '__main__':
    pass
