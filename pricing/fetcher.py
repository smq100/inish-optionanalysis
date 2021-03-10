''' Data fetcher'''

import datetime
import configparser

import quandl
import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay

from utils import utils as u

logger = u.get_logger()

quandl_config = configparser.ConfigParser()
quandl_config.read('config.ini')
quandl.ApiConfig.api_key = quandl_config['DEFAULT']['APIKEY']


def validate_ticker(ticker):
    return len(yf.Ticker(ticker).history(period="1d")) > 0

def get_company(ticker):
    '''
    Retrieves a company object that may be used to gather numerous data about the company and security.

    Attributes include:
        .info
        .history(start="2010-01-01",  end=”2020-07-21”)
        .actions
        .dividends
        .splits
        .sustainability
        .recommendations
        .calendar
        .isin
        .options

    :return: <object> YFinance Ticker object
    '''

    if validate_ticker(ticker):
        return yf.Ticker(ticker)
    else:
        return None

def get_current_price(ticker):
    if validate_ticker(ticker):
        start = datetime.datetime.today() - datetime.timedelta(days=5)
        df = get_ranged_data(ticker, start)
        price = df.iloc[-1]['Close']
    else:
        logger.error(f'Ticker {ticker} not valid')
        price = -1.0

    return price

def get_ranged_data(ticker, start, end=None):
    df = pd.DataFrame()

    if not end:
        end = datetime.date.today()

    if validate_ticker(ticker):
        company = get_company(ticker)
        info = company.history(start=f'{start:%Y-%m-%d}', end=f'{end:%Y-%m-%d}')
        df = pd.DataFrame(info)

    return df

def get_data(ticker):
    df = pd.DataFrame()

    if validate_ticker(ticker):
        company = get_company(ticker)
        info = company.history()
        df = pd.DataFrame(info)

    return df

def get_treasury_rate(ticker='DTB3'):
    # DTB3: Default to 3-Month Treasury Rate
    df = pd.DataFrame()
    prev_business_date = datetime.datetime.today() - BDay(1)

    df = quandl.get('FRED/' + ticker)
    if df.empty:
        logger.error('Unable to get Treasury Rates from Quandl. Please check connection')
        raise IOError('Unable to get Treasury Rate from Quandl')

    return df['Value'][0] / 100.0


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=10)
    end = datetime.datetime.today() - datetime.timedelta(days=5)

    df = get_data('WMT')
    print(df.tail())

    df = get_ranged_data('AAPL', start, end)
    print(df.tail())

    rate = get_treasury_rate()
    print(rate)
