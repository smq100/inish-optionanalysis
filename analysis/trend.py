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
            self.ticker = ticker.upper()
            self.history = None
            self.price = 0.0
            self.points = 0
            self.lines = []

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

            self.price = get_current_price(ticker)

            logger.info(f'Initialized SupportResitance for {ticker} (${self.price:.2f})')
        else:
            logger.info('Error initializing SupportResitance')


    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'


    def calculate(self, points):
        if self.history is not None and points > 100:
            self.points = points
            self.lines = []

            # Calculate support and resistance lines
            maxs = trendln.calc_support_resistance((None, sr.history[-points:].High), accuracy=2) #resistance
            mins = trendln.calc_support_resistance((sr.history[-points:].Low, None), accuracy=2)  #support

            maximaIdxs, pmax, maxtrend, maxwindows = maxs
            for window in maxtrend:
                self.lines += [{
                    'support':False,
                    'end_point': 0.0,
                    'points':window[0],
                    'slope':window[1][0],
                    'intercept':window[1][1],
                    'ssr':window[1][2],
                    'slope_err':window[1][3],
                    'intercept_err':window[1][4],
                    'area_avg':window[1][5]}]

            minimaIdxs, pmin, mintrend, minwindows = mins
            for window in mintrend:
                self.lines += [{
                    'support':True,
                    'end_point': 0.0,
                    'points':window[0],
                    'slope':window[1][0],
                    'intercept':window[1][1],
                    'ssr':window[1][2],
                    'slope_err':window[1][3],
                    'intercept_err':window[1][4],
                    'area_avg':window[1][5]}]

            logger.debug(f'{len(self.get_resistance())} total resistance lines')
            logger.debug(f'{len(self.get_support())} total support lines')

            # Find the relevant lines and calculate endpoints
            self._identify_relevant_lines()

    def get_resistance(self):
        resistance = []
        for line in self.lines:
            if not line['support']:
                resistance += [line]

        return resistance


    def get_support(self):
        support = []
        for line in self.lines:
            if line['support']:
                support += [line]

        return support


    def _identify_relevant_lines(self, min_width=50, best=3):
        # Enforce min width between pivot end points
        for index, line in enumerate(self.lines):
            if max(line['points']) - min(line['points']) < min_width:
                self.lines.pop(index)

        logger.debug(f'{len(self.get_resistance())} relevant resistance lines')
        logger.debug(f'{len(self.get_support())} relevant support lines')

        # Calculate end point extensions
        for line in self.lines:
            line['end_point'] = (self.points * line['slope']) + line['intercept']

        # Based on extension, maybe some support lines are now resistance, and vice versa
        for index, line in enumerate(self.lines):
            if line['support']:
                if line['end_point'] > self.price:
                    line['support'] = False
            elif line['end_point'] < self.price:
                line['support'] = True

        # Sort and Prune
        sup = sorted(self.get_support(), reverse=True, key=lambda k: k['area_avg'])
        sup = sup[:best]
        res = sorted(self.get_resistance(), reverse=True, key=lambda k: k['area_avg'])
        res = res[:best]
        self.lines = res + sup

        for line in self.get_resistance():
            line = f'Res: m={line["slope"]:.3f}, '\
                        f'b={line["intercept"]:.1f}, '\
                        f's={line["points"][0]}/{line["points"][-1]}({len(line["points"])}/{self.points}), '\
                        f'x={line["end_point"]:.2f}, '\
                        f'a={line["area_avg"]:.3f}'
            logger.debug(line)

        for line in self.get_support():
            line = f'Sup: m={line["slope"]:.3f}, '\
                        f'b={line["intercept"]:.1f}, '\
                        f's={line["points"][0]}/{line["points"][-1]}({len(line["points"])}/{self.points}), '\
                        f'x={line["end_point"]:.2f}, '\
                        f'a={line["area_avg"]:.3f}'
            logger.debug(line)


if __name__ == '__main__':
    import logging
    u.get_logger(logging.DEBUG)

    start = datetime.datetime.today() - datetime.timedelta(days=1000)
    sr = SupportResistance('MSFT', start=start)
    sr.calculate(300)

    fig = trendln.plot_support_resistance((None, sr.history[-300:].High), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], None), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], sr.history[-300:].High), accuracy=2)
    fig.savefig('figure')