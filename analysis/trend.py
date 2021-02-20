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


class Line:
    def __init__(self):
        self.support = False
        self.score = 0.0
        self.end_point = 0.0
        self.points = []
        self.slope = 0.0
        self.intercept = 0.0
        self.ssr = 0.0
        self.slope_err = 0.0
        self.intercept_err = 0.0
        self.area_avg = 0.0

    def __str__(self):
        dates = []
        for point in self.points:
            dates += point['date']

        output = f'ssr={self.ssr:.1e}, '\
                 f'se={self.slope_err:.1e}, '\
                 f'ie={self.intercept_err:.1e}, '\
                 f'a={self.area_avg:.3f}, '\
                 f'd={dates}, '\
                 f's={self.score:.1e}, '\
                 f'x={self.end_point:.2f} '

        return output

    def calculate(self):
        self.score = (self.area_avg * 1000) / (self.intercept_err * self.slope_err * self.ssr)

class SupportResistance:
    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.history = None
            self.price = 0.0
            self.lines = []
            self.method = trendln.METHOD_NAIVECONSEC    # METHOD_NAIVE, METHOD_NAIVECONSEC, METHOD_NUMDIFF
            self.extmethod = trendln.METHOD_NSQUREDLOGN # METHOD_NCUBED, METHOD_NSQUREDLOGN, METHOD_HOUGHPOINTS, METHOD_HOUGHLINES, METHOD_PROBHOUGH

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

            self.points = len(self.history)
            self.price = get_current_price(ticker)

            logger.info(f'Initialized SupportResitance for {ticker} (${self.price:.2f})')
            logger.info(f'{self.points} points from {self.history.iloc[0].name} to {self.history.iloc[-1].name}')
        else:
            logger.info('Error initializing SupportResitance')

    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'

    def calculate(self):
        if self.history is not None:
            self.lines = []

            # Calculate support and resistance lines
            maxs = trendln.calc_support_resistance((None, self.history.High), method=self.method, accuracy=2) #resistance
            mins = trendln.calc_support_resistance((self.history.Low, None), method=self.method, accuracy=2)  #support

            maximaIdxs, pmax, maxtrend, maxwindows = maxs
            for line in maxtrend:
                newline = Line()
                newline.support = False
                newline.score = 0.0
                newline.end_point = 0.0
                newline.points = []
                newline.slope = line[1][0]
                newline.intercept = line[1][1]
                newline.ssr = line[1][2]
                newline.slope_err = line[1][3]
                newline.intercept_err = line[1][4]
                newline.area_avg = line[1][5]

                self.lines += [newline]
                for point in line[0]:
                    self.lines[-1].points += [{'index':point, 'date':''}]

            minimaIdxs, pmin, mintrend, minwindows = mins
            for line in mintrend:
                newline = Line()
                newline.support = True
                newline.score = 0.0
                newline.end_point = 0.0
                newline.points = []
                newline.slope = line[1][0]
                newline.intercept = line[1][1]
                newline.ssr = line[1][2]
                newline.slope_err = line[1][3]
                newline.intercept_err = line[1][4]
                newline.area_avg = line[1][5]

                self.lines += [newline]
                for point in line[0]:
                    self.lines[-1].points += [{'index':point, 'date':''}]

            logger.debug(f'{len(self.get_resistance())} total resistance lines')
            logger.debug(f'{len(self.get_support())} total support lines')

            # Find the relevant lines and calculate endpoints
            self._identify_relevant_lines()

    def get_resistance(self):
        resistance = []
        for line in self.lines:
            if not line.support:
                resistance += [line]

        return resistance

    def get_support(self):
        support = []
        for line in self.lines:
            if line.support:
                support += [line]

        return support

    def _identify_relevant_lines(self, min_width=50, best=3):
        # Enforce min width between pivot end points
        for index, line in enumerate(self.lines):
            if line.points[-1]['index'] - line.points[0]['index'] < min_width:
                self.lines.pop(index)

        logger.debug(f'{len(self.get_resistance())} relevant resistance lines')
        logger.debug(f'{len(self.get_support())} relevant support lines')

        # Calculate end point extensions
        for line in self.lines:
            line.end_point = (self.points * line.slope) + line.intercept

        # Based on extension, maybe some support lines are now resistance, and vice versa
        # for index, line in enumerate(self.lines):
        #     if line['support']:
        #         if line['end_point'] > self.price:
        #             line['support'] = False
        #     elif line['end_point'] < self.price:
        #         line['support'] = True

        # Calculate dates of pivit points
        for line in self.lines:
            for point in line.points:
                date = self.history.iloc[point['index']].name
                point['date'] = [date.date().strftime('%Y-%m-%d')]

        # Calculate final score
        for line in self.lines:
            line.calculate()

        # Sort and Prune
        sup = sorted(self.get_support(), reverse=True, key=lambda k: k.score)
        sup = sup[:best]
        res = sorted(self.get_resistance(), reverse=True, key=lambda k: k.score)
        res = res[:best]
        self.lines = res + sup

        for line in self.get_resistance():
            line = f'Res:{line}'
            logger.debug(line)

        for line in self.get_support():
            line = f'Sup:{line}'
            logger.debug(line)


if __name__ == '__main__':
    import logging
    u.get_logger(logging.DEBUG)

    start = datetime.datetime.today() - datetime.timedelta(days=240)
    sr = SupportResistance('MSFT', start=start)
    sr.calculate()

    fig = trendln.plot_support_resistance((None, sr.history.High), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], None), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], sr.history[-300:].High), accuracy=2)
    fig.savefig('figure')