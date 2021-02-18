'''
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime

import yfinance as yf
import trendln
import matplotlib.pyplot as plt

from pricing.fetcher import validate_ticker, get_current_price
from utils import utils as u

logger = u.get_logger()

class SupportResistance:
    '''TODO'''

    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            logger.info('Initializing SupportResitance...')

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
        else:
            logger.info('Error initializing SupportResitance')


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

            # Calculate support and resistance lines
            mins = trendln.calc_support_resistance((sr.history[-points:].Low, None), accuracy=2)  #support
            maxs = trendln.calc_support_resistance((None, sr.history[-points:].High), accuracy=2) #resistance

            minimaIdxs, pmin, mintrend, minwindows = mins
            for window in mintrend:
                self._support += [{
                    'relevant':False,
                    'points':window[0],
                    'slope':window[1][0],
                    'intercept':window[1][1],
                    'ssr':window[1][2],
                    'slope_err':window[1][3],
                    'intercept_err':window[1][4],
                    'area_avg':window[1][5]}]

            maximaIdxs, pmax, maxtrend, maxwindows = maxs
            for window in maxtrend:
                self._resistance += [{
                    'relevant':False,
                    'points':window[0],
                    'slope':window[1][0],
                    'intercept':window[1][1],
                    'ssr':window[1][2],
                    'slope_err':window[1][3],
                    'intercept_err':window[1][4],
                    'area_avg':window[1][5]}]

            logger.debug(f'Found {len(self._support)} total support lines')
            logger.debug(f'Found {len(self._resistance)} total resistance lines')

            # Find the relevant lines and calculate endpoints
            self._find_relevant_lines(points)
            self._calc_endpoints()


    def _find_relevant_lines(self, points, end_distance=100, min_width=10, best=5, remove=False):
        # Find relevant lines
        for line in self._support:
            if max(line['points']) >= (points - end_distance):
                if max(line['points']) - min(line['points']) >= min_width:
                    line['relevant'] = True
                    break

        for line in self._resistance:
            if max(line['points']) >= (points - end_distance):
                if max(line['points']) - min(line['points']) >= min_width:
                    line['relevant'] = True
                    break

        # Remove irrelevant lines if desired
        if remove:
            for index, line in enumerate(self._support):
                if not line['relevant']:
                    self._support.pop(index)

            for index, line in enumerate(self._resistance):
                if not line['relevant']:
                    self._resistance.pop(index)

        # Find the best and reverse order from best to worst. Items are sorted by calc_support_resistance() in acsending order of 'area_avg'
        self.support_lines = []
        for line in self._support:
            if line['relevant']:
                self.support_lines += [
                    {'slope':line['slope'],
                    'intercept':line['intercept'],
                    'start':line['points'][0],
                    'stop':line['points'][-1],
                    'area':line['area_avg']}]

                line = f'Sup: m={line["slope"]:.2f}, '\
                            f'b={line["intercept"]:.1f}, '\
                            f's={line["points"][0]}/{line["points"][-1]}({self.points}), '\
                            f'a={line["area_avg"]:.3f}'
                logger.debug(line)

        # Save the best, and reverse order
        self.support_lines = self.support_lines[-best:]
        self.support_lines = self.support_lines[::-1]

        logger.debug(f'Identified {len(self.support_lines)} relevant support lines')

        self.resistance_lines = []
        for line in self._resistance:
            if line['relevant']:
                self.resistance_lines += [
                    {'slope':line['slope'],
                    'intercept':line['intercept'],
                    'start':line['points'][0],
                    'stop':line['points'][-1],
                    'area':line['area_avg']}]

                line = f'Res: m={line["slope"]:.2f}, '\
                            f'b={line["intercept"]:.1f}, '\
                            f's={line["points"][0]}/{line["points"][-1]}({self.points}), '\
                            f'a={line["area_avg"]:.3f}'
                logger.debug(line)

        # Save the best, and reverse order
        self.resistance_lines = self.resistance_lines[-best:]
        self.resistance_lines = self.resistance_lines[::-1]

        logger.debug(f'Identified {len(self.resistance_lines)} relevant resistance lines')


    def _calc_endpoints(self):
        self.resistance_points = []
        self.support_points = []

        for line in self.resistance_lines:
            point = (self.points * line['slope']) + line['intercept']
            if point > 0.0 and point > self.price:
                self.resistance_points += [point]

        for line in self.support_lines:
            point = (self.points * line['slope']) + line['intercept']
            if point > 0.0 and point < self.price:
                self.support_points += [point]

        # Sort values by relevance to current price
        self.resistance_points.sort()
        self.support_points.sort(reverse=True)

        logger.debug(f'Res: {self.ticker}@{self.price:.2f}: {self.resistance_points}')
        logger.debug(f'Sup: {self.ticker}@{self.price:.2f}: {self.support_points}')


if __name__ == '__main__':
    start = datetime.datetime.today() - datetime.timedelta(days=1000)
    sr = SupportResistance('MSFT', start=start)
    sr.calculate(300)

    # fig = trendln.plot_support_resistance((None, sr.history[-300:].High), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], None), accuracy=2)
    fig = trendln.plot_support_resistance((sr.history.Low[-300:], sr.history[-300:].High), accuracy=2)
    fig.savefig('figure')