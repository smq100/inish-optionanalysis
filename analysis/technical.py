'''
ta: https://technical-analysis-library-in-python.readthedocs.io/en/latest/index.html
'''

import pandas as pd
from ta import trend, momentum, volatility, volume

from data import store as store
from utils import utils as utils


class Technical:
    def __init__(self, ticker:str, history:pd.DataFrame, days:int, live:bool=False):
        if store.is_ticker(ticker):
            self.ticker = ticker.upper()
            self.days = days

            if history is None or history.empty:
                self.history = store.get_history(self.ticker, self.days, live=live)
            else:
                self.history = history

        else:
            raise ValueError('Invalid symbol')

    def __str__(self):
        return f'Technical analysis for {self.ticker}'

    def calc_sma(self, interval:int) -> pd.DataFrame:
        df = pd.DataFrame()
        if interval > 5 and interval < self.days:
            df = trend.sma_indicator(self.history['close'], window=interval, fillna=True)

        return df

    def calc_ema(self, interval:int) -> pd.DataFrame:
        df = pd.DataFrame()
        if interval > 5 and interval < self.days:
            df = trend.ema_indicator(self.history['close'], window=interval, fillna=True)

        return df

    def calc_rsi(self, interval:int=14) -> pd.DataFrame:
        df = pd.DataFrame()
        if interval > 5 and interval < self.days:
            df = momentum.rsi(self.history['close'], window=interval, fillna=True)

        return df

    def calc_vwap(self) -> pd.DataFrame:
        df = pd.DataFrame()
        vwap = volume.VolumeWeightedAveragePrice(self.history['high'], self.history['low'], self.history['close'], self.history['volume'], fillna=True)
        df = vwap.volume_weighted_average_price()

        return df

    def calc_macd(self, slow:int=26, fast:int=12, signal:int=9) -> pd.DataFrame:
        df = pd.DataFrame()
        macd = trend.MACD(self.history['close'], window_slow=slow, window_fast=fast, window_sign=signal, fillna=True)
        diff = macd.macd_diff()
        macd_ = macd.macd()
        signal = macd.macd_signal()

        df = pd.concat([diff, macd_, signal], axis=1)
        df.columns = ['Diff', 'MACD', 'Signal']

        return df

    def calc_bb(self, interval:int=14, std:int=2) -> pd.DataFrame:
        df = pd.DataFrame()
        if interval > 5 and interval < self.days:
            bb = volatility.BollingerBands(self.history['close'], window=interval, window_dev=std, fillna=True)
            high = bb.bollinger_hband()
            mid = bb.bollinger_mavg()
            low = bb.bollinger_lband()

            df = pd.concat([high, mid, low], axis=1)
            df.columns = ['High', 'Mid', 'Low']

        return df

if __name__ == '__main__':
    ta = Technical('AAPL', None, 365)
    value = ta.calc_sma(21).iloc[-1]
    print(value)
