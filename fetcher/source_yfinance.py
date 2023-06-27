'''
yfinance: https://github.com/ranaroussi/yfinance
'''

import time
import datetime as dt

import pandas as pd
import yfinance as yf

import data as d
from utils import ui, logger


YAHOO_INFO_DISABLED = True

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
        try:
            company = yf.Ticker(ticker)
        except Exception as e:
            _logger.error(f'yfinance exception creating Ticker: {e}: {ticker}')
        else:
            _logger.info(f'Fetched company information for {ticker} from Yahoo')

    _last_company = company
    _last_ticker = ticker

    return company


def get_history(ticker: str, days: int = -1) -> pd.DataFrame:
    history = pd.DataFrame()
    company = get_company(ticker)

    if company is None:
        _logger.error(f'\'None\' object for {ticker}')
    else:
        if days < 0:
            days = 7300  # 20 years

        if days > 0:
            end = dt.datetime.today()
            start = end - dt.timedelta(days=days)

            for retry in range(RETRIES):
                try:
                    history = company.history(start=start, end=end, interval='1d', timeout=2.0, back_adjust=True)

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
                    _logger.error(f'Error during attempt {retry+1} to fetch history of {ticker} from {d.ACTIVE_HISTORYDATASOURCE}: {e}')
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


def get_ratings(ticker: str) -> list[int]:
    ratings = pd.DataFrame()
    results = []

    if not YAHOO_INFO_DISABLED:
        if d.ACTIVE_OPTIONDATASOURCE == 'etrade':
            _logger.warning('Option datasource is E*Trade but using YFinance to fetch ratings')

        try:
            company = yf.Ticker(ticker)
            if company is not None:
                ratings = company.recommendations
                if ratings is not None and not ratings.empty:
                    # Clean up and normalize text
                    ratings = ratings.reset_index()
                    ratings = ratings.sort_values('Date', ascending=True)
                    ratings = ratings.tail(10)
                    ratings = ratings['To Grade'].replace(' ', '', regex=True)
                    ratings = ratings.replace('-', '', regex=True)
                    ratings = ratings.replace('_', '', regex=True)

                    results = ratings.str.lower().tolist()

                    # Log any unhandled ranking so we can add it to the ratings list
                    [_logger.warning(f'Unhandled rating: {r} for {ticker}') for r in results if not r in d.RATINGS]

                    # Use the known ratings and convert to their numeric values
                    results = [r for r in results if r in d.RATINGS]
                    results = [d.RATINGS[r] for r in results]
                else:
                    _logger.info(f'No ratings for {ticker}')
            else:
                _logger.info(f'Unable to get ratings for {ticker}. No company info')
        except Exception as e:
            results = []
            _logger.error(f'Unable to get ratings for {ticker}: {str(e)}')
        else:
            _logger.info(f'Fetched Yahoo rating information for {ticker}')

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        ticker = get_company(sys.argv[1])
    else:
        ticker = get_company('aapl')

    print(ticker.info)
