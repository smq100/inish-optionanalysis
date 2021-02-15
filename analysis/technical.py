'''
    ta:      https://technical-analysis-library-in-python.readthedocs.io/en/latest/index.html
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime
import logging

import yfinance as yf
import pandas as pd
from ta import trend, momentum, volatility, volume

from pricing.fetcher import validate_ticker
from utils import utils as u


class TechnicalAnalysis():
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

            logging.info('Initialized TechnicalAnalysis')
        else:
            logging.info('Error initializing TechnicalAnalysis')

    def __str__(self):
        return f'Technical analysis for {self.ticker}'


    def calc_ema(self, interval):
        df = pd.DataFrame()

        if interval > 5:
            df = trend.ema_indicator(self.history['Close'], window=interval, fillna=True)

        return df


    def calc_rsi(self, interval=14):
        df = pd.DataFrame()

        if interval > 5:
            df = momentum.rsi(self.history['Close'], window=interval, fillna=True)

        return df


    def calc_vwap(self):
        df = pd.DataFrame()

        vwap = volume.VolumeWeightedAveragePrice(self.history['High'], self.history['Low'], self.history['Close'], self.history['Volume'], fillna=True)
        df = vwap.volume_weighted_average_price()

        return df


    def calc_macd(self, slow=26, fast=12, signal=9):
        macd = trend.MACD(self.history['Close'], window_slow=slow, window_fast=fast, window_sign=signal, fillna=True)
        diff = macd.macd_diff()
        macd_ = macd.macd()
        signal = macd.macd_signal()

        df = pd.concat([diff, macd_, signal], axis=1)
        df.columns = ['Diff', 'MACD', 'Signal']

        return df


    def calc_bb(self, interval=14, std=2):
        df = pd.DataFrame()

        if interval > 5:
            bb = volatility.BollingerBands(self.history['Close'], window=interval, window_dev=std, fillna=True)
            high = bb.bollinger_hband()
            mid = bb.bollinger_mavg()
            low = bb.bollinger_lband()

            df = pd.concat([high, mid, low], axis=1)
            df.columns = ['High', 'Mid', 'Low']

        return df


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=365)
    ta = TechnicalAnalysis('AAPL', start)
    # data = ta.calc_macd()
    # data = ta.calc_ema(20)
    data = ta.calc_bb()
    # data = ta.calc_vwap()

    print(data.iloc[-1]['High'])
    # print(data)
