''' Data fetcher'''
import datetime
import logging
import configparser

import quandl
import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay
from pandas_datareader import data

from utils import utils as u

logging.basicConfig(format='%(levelname)s: %(message)s', level=u.LOG_LEVEL)

config = configparser.ConfigParser()
config.read('config.ini')
quandl.ApiConfig.api_key = config['DEFAULT']['APIKEY']

SOURCES = ['yahoo', 'morningstar']

def get_company_info(ticker):
    '''TODO'''

    return yf.Ticker(ticker)


def validate_ticker(ticker):
    '''Perform quick check to see if a ticker is valid'''

    start = datetime.datetime.today() - datetime.timedelta(days=3)

    try:
        data.DataReader(ticker, 'yahoo', start, None)
        return True
    except:
        return False


def get_ranged_data(ticker, start, end=None, use_quandl=True):
    ''' TODO '''

    dframe = pd.DataFrame()

    if not end:
        end = datetime.date.today()
    if use_quandl:
        logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
        dframe = quandl.get('WIKI/' + ticker, start_date=start, end_date=end)
    else:
        for source in SOURCES:
            logging.info('Fetching data for Ticker=%s from Source=%s', ticker, source)
            dframe = data.DataReader(ticker, source, start, end)

            if not dframe.empty:
                logging.info('Successfully fetched data')
                break

    return dframe


def get_data(ticker, use_quandl=True):
    ''' TODO '''

    dframe = pd.DataFrame()
    if use_quandl:
        logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
        dframe = quandl.get('WIKI/' + ticker)
        logging.info('Successfully fetched data')
    else:
        for source in SOURCES:
            logging.info('Fetching data for Ticker=%s from Source=%s', ticker, source)
            dframe = data.DataReader(ticker, source)
            if not dframe.empty:
                logging.info('Successfully fetched data')
                break

    return dframe


def get_treasury_rate(ticker=None):
    ''' TODO '''

    dframe = pd.DataFrame()
    if not ticker:
        ticker = 'DTB3'  # Default to 3-Month Treasury Rate
    prev_business_date = datetime.datetime.today() - BDay(1)
    logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
    dframe = quandl.get('FRED/' + ticker, start_date=prev_business_date - BDay(1), end_date=prev_business_date)
    if dframe.empty:
        logging.error('Unable to get Treasury Rates from Quandl. Please check connection')
        raise IOError('Unable to get Treasury Rate from Quandl')

    return dframe['Value'][0]


def get_spx_prices(start_date=None):
    ''' TODO '''

    if not start_date:
        start_date = datetime.datetime(2017, 1, 1)
    dframe = pd.DataFrame()
    dframe = get_data('SPX', False)
    if dframe.empty:
        logging.error('Unable to get SNP 500 Index from Web. Please check connection')
        raise IOError('Unable to get Treasury Rate from Web')

    return dframe


if __name__ == '__main__':
    start_ = datetime.datetime.today() + datetime.timedelta(days=-10)
    end_ = datetime.datetime.today() + datetime.timedelta(days=-5)
    # d_f = get_ranged_data('AAPL', start1_, end1_, use_quandl=True)
    # print(d_f.tail())

    d_f = get_data('WMT', use_quandl=True)
    print(d_f.tail())

    rate1 = get_treasury_rate()
    print(rate1)
