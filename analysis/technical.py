'''
ta: https://technical-analysis-library-in-python.readthedocs.io/en/latest/index.html
'''

import pandas as pd
from ta import trend, momentum, volatility, volume

from data import store as store
from utils import ui, logger

_logger = logger.get_logger()


class Technical:
    def __init__(self, ticker: str, history: pd.DataFrame, days: int, end: int = 0, live: bool = False):
        if store.is_ticker(ticker):
            self.ticker = ticker.upper()
            self.days = days
            self.end = end

            if history is None or history.empty:
                self.history = store.get_history(self.ticker, self.days, end=self.end, live=live)
            else:
                self.history = history
        else:
            raise ValueError('Invalid symbol')

    def __repr__(self):
        return f'<Technical Analysis ({self.ticker})>'

    def __str__(self):
        return f'{len(self.history)} items for {self.ticker}'

    def calc_sma(self, interval: int) -> pd.Series:
        df = pd.Series(dtype=float)
        if interval > 5 and interval < self.days:
            df = trend.sma_indicator(self.history['close'], window=interval, fillna=True)
        else:
            _logger.warning(f'{__name__}: Invalid interval for SMA')

        return df

    def calc_ema(self, interval: int) -> pd.Series:
        df = pd.Series(dtype=float)
        if interval > 5 and interval < self.days:
            df = trend.ema_indicator(self.history['close'], window=interval, fillna=True)
        else:
            _logger.warning(f'{__name__}: Invalid interval for EMA')

        return df

    def calc_rsi(self, interval: int = 14) -> pd.Series:
        df = pd.Series(dtype=float)
        if interval > 5 and interval < self.days:
            df = momentum.rsi(self.history['close'], window=interval, fillna=True)
        else:
            _logger.warning(f'{__name__}: Invalid interval for RSI')

        return df

    def calc_vwap(self) -> pd.Series:
        df = pd.Series(dtype=float)
        vwap = volume.VolumeWeightedAveragePrice(self.history['high'], self.history['low'], self.history['close'], self.history['volume'], fillna=True)
        df = vwap.volume_weighted_average_price()

        return df

    def calc_macd(self, slow: int = 26, fast: int = 12, signal: int = 9) -> pd.DataFrame:
        df = pd.DataFrame()
        macd = trend.MACD(self.history['close'], window_slow=slow, window_fast=fast, window_sign=signal, fillna=True)
        diff = macd.macd_diff()
        macd_ = macd.macd()
        signal = macd.macd_signal()

        df = pd.concat([diff, macd_, signal], axis=1)
        df.columns = ['Diff', 'MACD', 'Signal']

        return df

    def calc_bb(self, interval: int = 14, std: int = 2) -> pd.DataFrame:
        df = pd.DataFrame()
        if interval > 5 and interval < self.days:
            bb = volatility.BollingerBands(self.history['close'], window=interval, window_dev=std, fillna=True)
            high = bb.bollinger_hband()
            mid = bb.bollinger_mavg()
            low = bb.bollinger_lband()

            df = pd.concat([high, mid, low], axis=1)
            df.columns = ['High', 'Mid', 'Low']
        else:
            _logger.warning(f'{__name__}: Invalid interval for BB')

        return df


if __name__ == '__main__':
    ta = Technical('HLT', None, 365)
    value = ta.calc_rsi().iloc[-1]
    print(f'{value:.2f}')
