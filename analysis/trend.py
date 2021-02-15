'''
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime
import logging

import yfinance as yf
import trendln
import matplotlib.pyplot as plt

from pricing.fetcher import validate_ticker, get_current_price
from utils import utils as u


class SupportResistance:
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.history = None
            self.price = 0.0
            self.resistance_lines = []
            self.support_lines = []
            self._resistance = []
            self._support = []

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

            self.price = get_current_price(ticker)
            print(self.price)

            logging.info('Initialized SupportResitance')
        else:
            logging.info('Error initializing trend analysis')


    def __str__(self):
        return f'Support and resistance analysis for {self.ticker}'


    def calculate(self, points):
        if self.history is not None and points > 100:
            self.points = points
            self.resistance_lines = []
            self.support_lines = []
            self.resistance_points = []
            self.support_points = []
            self._resistance = []
            self._support = []

            minimaIdxs, pmin, mintrend, minwindows = trendln.calc_support_resistance((sr.history[-points:].Low, None), accuracy=2)  #support
            maximaIdxs, pmax, maxtrend, maxwindows = trendln.calc_support_resistance((None, sr.history[-points:].High), accuracy=2) #resistance

            for window in mintrend:
                self._support += [
                    {'relevant':False,
                    'points':window[0],
                    'line':
                        {'slope':window[1][0],
                        'intercept':window[1][1],
                        'ssr':window[1][2],
                        'slope_err':window[1][3],
                        'intercept_err':window[1][4],
                        'area_avg':window[1][5]}}]

            for window in maxtrend:
                self._resistance += [
                    {'relevant':False,
                    'points':window[0],
                    'line':
                        {'slope':window[1][0],
                        'intercept':window[1][1],
                        'ssr':window[1][2],
                        'slope_err':window[1][3],
                        'intercept_err':window[1][4],
                        'area_avg':window[1][5]}}]

            # Find the relevant lines
            self._find_relevant(points)


    def _find_relevant(self, points, threshold=10, best=4, remove=True):
        # Find relevant lines
        for line in self._resistance:
            for point in line['points']:
                if point >= (points - threshold):
                    line['relevant'] = True
                    break

        for line in self._support:
            for point in line['points']:
                if point >= (points - threshold):
                    line['relevant'] = True
                    break

        # Remove irrelevant lines
        if remove:
            for index, line in enumerate(self._resistance):
                if not line['relevant']:
                    self._resistance.pop(index)

            for index, line in enumerate(self._support):
                if not line['relevant']:
                    self._support.pop(index)

        # Find the best and reverse order from best to worst. Items are sorted by calc_support_resistance() in acsending order of 'area_avg'
        self._resistance = self._resistance[-best:]
        self._resistance = self._resistance[::-1]
        for line in self._resistance:
            self.resistance_lines += [(line['line']['slope'], line['line']['intercept'], line['line']['area_avg'])]

        logging.debug(f'RLines: {self.resistance_lines}')

        self._support = self._support[-best:]
        self._support = self._support[::-1]
        for line in self._support:
            self.support_lines += [(line['line']['slope'], line['line']['intercept'], line['line']['area_avg'])]

        logging.debug(f'SLines: {self.support_lines}')

        self._calc_endpoints()


    def _calc_endpoints(self):
        self.resistance_points = []
        self.support_points = []

        for line in self.resistance_lines:
            point = (self.points * line[0]) + line[1]
            if point > 0.0:
                self.resistance_points += [point]

        for line in self.support_lines:
            point = (self.points * line[0]) + line[1]
            if point > 0.0:
                self.support_points += [point]

        # Sort values by relevance to current price
        self.resistance_points.sort()
        self.support_points.sort(reverse=True)

        logging.info(f'Resistance Points: {self.resistance_points}')
        logging.info(f'Support Points: {self.support_points}')


if __name__ == '__main__':
    logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
    start = datetime.datetime.today() - datetime.timedelta(days=1000)
    sr = SupportResistance('IBM', start=start)
    sr.calculate(300)

    # idx = sr.history[-300:].index
    fig = trendln.plot_support_resistance((sr.history.Low[-300:], sr.history[-300:].High), accuracy=2)
    # fig = trendln.plot_sup_res_date((None, sr.history[-300:].High), idx, accuracy=2)
    fig.savefig('figure')