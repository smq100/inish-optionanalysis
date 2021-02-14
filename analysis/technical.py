'''TODO'''

import datetime

import yfinance as yf
import pandas as pd
from ta import trend

from pricing.fetcher import validate_ticker


class TechnicalAnalysis():
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.macd_ = None

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max")
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}')

    def macd(self):
        col = ['Diff', 'MACD', 'Signal']
        macd_diff = trend.macd_diff(self.history['Close'], fillna=True)
        macd_ = trend.macd(self.history['Close'], fillna=True)
        macd_signal = trend.macd_signal(self.history['Close'], fillna=True)

        df = pd.concat([macd_diff, macd_, macd_signal], axis=1)
        df.columns = col
        self.macd_ = df

        return df


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=365)
    ta = TechnicalAnalysis('BBY', start)
    data = ta.macd()

    print(data.tail(n=10))
