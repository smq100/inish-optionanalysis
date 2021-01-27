''' Data fetcher'''
import datetime
import logging

import pandas as pd
import quandl
from pandas.tseries.offsets import BDay
from pandas_datareader import data

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

quandl.ApiConfig.api_key = 'dm53mzimZcmHWcA3gNV1'

SOURCES = ['yahoo', 'morningstar']


def get_ranged_data(ticker, start, end=None, use_quandl=True):
    ''' TODO '''
    dframe = pd.DataFrame()

    if not end:
        end = datetime.date.today()
    if use_quandl:
        logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
        dframe = quandl.get('WIKI/' + ticker, start_date=start, end_date=end)
        logging.info('### Successfully fetched data!!')
    else:
        for source in SOURCES:
            logging.info(
                'Fetching data for Ticker=%s from Source=%s', ticker, source)
            dframe = data.DataReader(ticker, source, start, end)
            if not dframe.empty:
                logging.info('### Successfully fetched data!')
                break
    return dframe


def get_data(ticker, use_quandl):
    ''' TODO '''
    dframe = pd.DataFrame()
    if use_quandl:
        logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
        dframe = quandl.get('WIKI/' + ticker)
        logging.info('### Successfully fetched data!!')
    else:
        for source in SOURCES:
            logging.info(
                'Fetching data for Ticker=%s from Source=%s', ticker, source)
            dframe = data.DataReader(ticker, source)
            if not dframe.empty:
                logging.info('### Successfully fetched data!!')
                break
    return dframe


def get_treasury_rate(ticker=None):
    ''' TODO '''
    dframe = pd.DataFrame()
    if not ticker:
        ticker = 'DTB3'  # Default to 3-Month Treasury Rate
    prev_business_date = datetime.datetime.today() - BDay(1)
    logging.info('Fetching data for Ticker=%s from Source=Quandl', ticker)
    dframe = quandl.get('FRED/' + ticker, start_date=prev_business_date -
                        BDay(1), end_date=prev_business_date)
    if dframe.empty:
        logging.error(
            'Unable to get Treasury Rates from Quandl. Please check connection')
        raise IOError('Unable to get Treasury Rate from Quandl')
    logging.info('### Successfully fetched data!!')
    print(dframe['Value'][0])
    return dframe['Value'][0]


def get_spx_prices(start_date=None):
    ''' TODO '''
    if not start_date:
        start_date = datetime.datetime(2017, 1, 1)
    dframe = pd.DataFrame()
    dframe = get_data('SPX', False)
    if dframe.empty:
        logging.error(
            'Unable to get SNP 500 Index from Web. Please check connection')
        raise IOError('Unable to get Treasury Rate from Web')
    return dframe


if __name__ == '__main__':
    # d_f = get_data('AAPL', datetime.datetime(2017, 1, 1), useQuandl=True)
    # d_f = get_data('SPX', datetime.datetime(2017, 1, 1), useQuandl=False)
    d_f = get_data('WMT', True)
    print(d_f.head())
    # print(d_f.tail())
    # rate = get_treasury_rate()
    # print type(rate), rate
