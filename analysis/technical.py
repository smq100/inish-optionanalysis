'''
ta: https://technical-analysis-library-in-python.readthedocs.io/en/latest/index.html
'''

import pandas as pd
from ta import trend, momentum, volatility, volume

from data import store as o
from utils import utils as u

logger = u.get_logger()


class Technical:
    def __init__(self, ticker, days=-1):
        if o.is_symbol_valid(ticker):
            self.ticker = ticker.upper()
            self.days = days
            self.history = o.get_history(self.ticker, self.days)
        else:
            raise ValueError('Invalid symbol')

    def __str__(self):
        return f'Technical analysis for {self.ticker}'

    def calc_sma(self, interval):
        df = pd.DataFrame()
        if interval > 5:
            df = trend.sma_indicator(self.history['close'], window=interval, fillna=True)

        return df

    def calc_ema(self, interval):
        df = pd.DataFrame()
        if interval > 5:
            df = trend.ema_indicator(self.history['close'], window=interval, fillna=True)

        return df

    def calc_rsi(self, interval=14):
        df = pd.DataFrame()
        if interval > 5:
            df = momentum.rsi(self.history['close'], window=interval, fillna=True)

        return df

    def calc_vwap(self):
        df = pd.DataFrame()
        vwap = volume.VolumeWeightedAveragePrice(self.history['high'], self.history['low'], self.history['close'], self.history['volume'], fillna=True)
        df = vwap.volume_weighted_average_price()

        return df

    def calc_macd(self, slow=26, fast=12, signal=9):
        df = pd.DataFrame()
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
    ta = Technical('AAPL', 365)
    value = ta.calc_sma(21).iloc[-1]
    print(value)
