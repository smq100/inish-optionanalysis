'''
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime

import yfinance as yf
import trendln
import matplotlib.pyplot as plt

from pricing.fetcher import validate_ticker


class SupportResistance:
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.history = None
            self.resistance = []
            self.support = []

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)


    def __str__(self):
        return f'Technical analysis for {self.ticker}'


    def calculate(self, points):
        if self.history is not None:
            self.resistance = []
            self.support = []

            minimaIdxs, pmin, mintrend, minwindows = trendln.calc_support_resistance((sr.history[-points:].Low, None), accuracy=2)  #support
            maximaIdxs, pmax, maxtrend, maxwindows = trendln.calc_support_resistance((None, sr.history[-points:].High), accuracy=2) #resistance

            for window in maxtrend:
                sr.resistance += [{'relavent':False, 'points':window[0],
                    'line':
                        {'slope':window[1][0],
                        'intercept':window[1][1],
                        'ssr':window[1][2],
                        'slope_err':window[1][3],
                        'intercept_err':window[1][4],
                        'area_avg':window[1][5]}}]

            for window in mintrend:
                sr.support += [{'relavent':False, 'points':window[0],
                    'line':
                        {'slope':window[1][0],
                        'intercept':window[1][1],
                        'ssr':window[1][2],
                        'slope_err':window[1][3],
                        'intercept_err':window[1][4],
                        'area_avg':window[1][5]}}]


    def _find_relavent(self, age, threshold=10, best=4, remove=True):
        # Find relavent items
        for line in self.resistance:
            for point in line['points']:
                if point >= (age - threshold):
                    line['relavent'] = True
                    break

        # Remove irrelavent items
        if remove:
            for index, line in enumerate(self.resistance):
                if not line['relavent']:
                    self.resistance.pop(index)

        # Find the best and reverse order from best to worst. Items are sorted by calc_support_resistance() in acsending order of 'area_avg'
        self.resistance = self.resistance[-best:]
        self.resistance = self.resistance[::-1]
        self.support = self.support[-best:]
        self.support = self.support[::-1]


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=1000)
    sr = SupportResistance('AAPL', start=start)

    sr.calculate(300)
    sr._find_relavent(300)

    for line in sr.resistance:
        print(line['points'])
        print(line['line']['area_avg'])

    # idx = sr.history[-300:].index
    # fig = trendln.plot_support_resistance((None, sr.history.High), accuracy=2)
    # fig = trendln.plot_sup_res_date((None, sr.history[-300:].High), idx, accuracy=2)
    # fig.savefig('figure')