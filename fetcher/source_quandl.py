import time
import datetime as dt
import configparser
from pathlib import Path

import quandl
import pandas as pd

import fetcher as f
import data as d
from utils import logger


_logger = logger.get_logger()


# Credentials
CREDENTIALS = Path(__file__).resolve().parent  / 'quandl.ini'
config = configparser.ConfigParser()
config.read(CREDENTIALS)
quandl.ApiConfig.api_key = config['DEFAULT']['APIKEY']


def get_history(ticker: str, days: int = -1) -> pd.DataFrame:
    history: pd.DataFrame = pd.DataFrame()

    if days < 0:
        days = 7300  # 20 years

    if days > 0:
        start = dt.datetime.today() - dt.timedelta(days=days)

        for retry in range(f.RETRIES):
            try:
                history = quandl.get_table(f'QUOTEMEDIA/PRICES',
                                       qopts={'columns': ['date', 'open', 'high', 'low', 'close', 'volume']},
                                       ticker=ticker, paginate=True, date={'gte': f'{start:%Y-%m-%d}'})
                days = history.shape[0]

                if history is None:
                    history = pd.DataFrame()
                    _logger.warning(f'{d.ACTIVE_HISTORYDATASOURCE} history for {ticker} is None ({retry+1})')
                    time.sleep(f.THROTTLE_ERROR)
                elif history.empty:
                    _logger.info(f'{d.ACTIVE_HISTORYDATASOURCE} history for {ticker} is empty ({retry+1})')
                    time.sleep(f.THROTTLE_ERROR)
                else:
                    history = history.reset_index()

                    # Clean some things up and make columns consistent with Postgres column names
                    history.columns = history.columns.str.lower()
                    history = history.drop(['none'], axis=1)
                    history = history.sort_values('date', ascending=True)

                    _logger.info(f'Fetched {days} days of live history of {ticker} starting {start:%Y-%m-%d}')
                    break
            except Exception as e:
                _logger.error(f'Exception: {e}: Retry {retry} to fetch history of {ticker} from {d.ACTIVE_HISTORYDATASOURCE}')
                history = pd.DataFrame()
                time.sleep(f.THROTTLE_ERROR)

    return history


def get_treasury_rate(ticker: str) -> float:
    df = pd.DataFrame()
    df = quandl.get(f'FRED/{ticker}')
    if df.empty:
        _logger.error('Unable to get Treasury Rates from Quandl')
        raise IOError('Unable to get Treasury Rate from Quandl')

    return df['Value'][0] / 100.0


if __name__ == '__main__':
    pass
