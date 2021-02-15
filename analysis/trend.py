'''
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime

import yfinance as yf
import trendln

from pricing.fetcher import validate_ticker


class SupportResistance:
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.max_lines = []
            self.min_lines = []

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)


    def __str__(self):
        return f'Technical analysis for {self.ticker}'


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=365)
    sr = SupportResistance('AAPL', start=start)

    minimaIdxs, pmin, mintrend, minwindows = trendln.calc_support_resistance((sr.history[-300:].Low, None), accuracy=2) #support
    maximaIdxs, pmax, maxtrend, maxwindows = trendln.calc_support_resistance((None, sr.history[-300:].High), accuracy=2) #resistance

    for window in maxtrend:
        sr.max_lines += [{'points':window[0], 'line':
            {'slope':window[1][0],
            'intercept':window[1][1],
            'ssr':window[1][2],
            'slope_err':window[1][3],
            'intercept_err':window[1][4],
            'area_avg':window[1][5]}}]

        # print(sr.max_lines[-1]['points'])
        print(sr.max_lines[-1]['line']['area_avg'])
