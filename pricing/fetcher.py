''' Data fetcher'''

import datetime
import logging
import configparser

import quandl
import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay

from utils import utils as u

logging.basicConfig(format='%(levelname)s: %(message)s', level=u.LOG_LEVEL)

quandl_config = configparser.ConfigParser()
quandl_config.read('config.ini')
quandl.ApiConfig.api_key = quandl_config['DEFAULT']['APIKEY']

SOURCE = 'yahoo'

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


def validate_ticker(ticker):
    '''Perform quick check to see if a ticker is valid'''

    try:
        data = yf.Ticker(ticker)
        return True
    except:
        return False


def get_current_price(ticker):
    if validate_ticker(ticker):
        start = datetime.datetime.today() - datetime.timedelta(days=5)
        df = get_ranged_data(ticker, start)
        price = df.iloc[-1]['Close']
    else:
        price = -1.0

    return price


def get_ranged_data(ticker, start, end=None):
    ''' TODO '''

    df = pd.DataFrame()

    if not end:
        end = datetime.date.today()

    if validate_ticker(ticker):
        company = get_company(ticker)
        info = company.history(start=f'{start:%Y-%m-%d}', end=f'{end:%Y-%m-%d}')
        df = pd.DataFrame(info)

    return df


def get_data(ticker):
    ''' TODO '''

    df = pd.DataFrame()

    if validate_ticker(ticker):
        company = get_company(ticker)
        info = company.history()
        df = pd.DataFrame(info)

    return df


def get_treasury_rate(ticker='DTB3'):
    ''' TODO '''

    # DTB3: Default to 3-Month Treasury Rate
    logging.info('Fetching data for Ticker=%s', ticker)

    df = pd.DataFrame()
    prev_business_date = datetime.datetime.today() - BDay(1)

    df = quandl.get('FRED/' + ticker, start_date=prev_business_date - BDay(1), end_date=prev_business_date)
    if df.empty:
        logging.error('Unable to get Treasury Rates from Quandl. Please check connection')
        raise IOError('Unable to get Treasury Rate from Quandl')

    return df['Value'][0]


def get_spx_prices(start_date=None):
    ''' TODO '''

    if start_date is None:
        start_date = datetime.datetime(2017, 1, 1)

    df = pd.DataFrame()
    df = get_data('SPX', False)

    if df.empty:
        logging.error('Unable to get SNP 500 Index from Web. Please check connection')
        raise IOError('Unable to get Treasury Rate from Web')

    return df


if __name__ == '__main__':
    start = datetime.datetime.today() + datetime.timedelta(days=-10)
    end = datetime.datetime.today() + datetime.timedelta(days=-5)

    df = get_ranged_data('AAPL', start, end)
    print(df.tail())

    df = get_data('WMT')
    print(df.tail())

    # rate1 = get_treasury_rate()
    # print(rate1)
