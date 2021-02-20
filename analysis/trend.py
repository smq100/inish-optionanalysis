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
            self.lines = []
            self.method = trendln.METHOD_NAIVECONSEC # METHOD_NAIVE, METHOD_NAIVECONSEC, METHOD_NUMDIFF
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
                self.lines += [{
                    'support':False,
                    'score':0.0,
                    'end_point':0.0,
                    'dates':[],
                    'points':line[0],
                    'slope':line[1][0],
                    'intercept':line[1][1],
                    'ssr':line[1][2],
                    'slope_err':line[1][3],
                    'intercept_err':line[1][4],
                    'area_avg':line[1][5]}]

            minimaIdxs, pmin, mintrend, minwindows = mins
            for line in mintrend:
                self.lines += [{
                    'support':True,
                    'score':0.0,
                    'end_point':0.0,
                    'dates':[],
                    'points':line[0],
                    'slope':line[1][0],
                    'intercept':line[1][1],
                    'ssr':line[1][2],
                    'slope_err':line[1][3],
                    'intercept_err':line[1][4],
                    'area_avg':line[1][5]}]

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
        # Inner function to calculate overall score
        def calculate_score(line):
            return (line['area_avg'] * 1000) / (line['intercept_err'] * line['slope_err'] * line['ssr'])

        # Inner function to get dates from points
        def dates_from_points_in_line(line):
            for points in line['points']:
                date = self.history.iloc[points].name
                line['dates'] += [date.date().strftime("%Y-%m-%d")]

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
        # for index, line in enumerate(self.lines):
        #     if line['support']:
        #         if line['end_point'] > self.price:
        #             line['support'] = False
        #     elif line['end_point'] < self.price:
        #         line['support'] = True

        # Calculate dates of pivit points
        for index, line in enumerate(self.lines):
            dates_from_points_in_line(line)

        # Calculate final score
        for line in self.lines:
            line['score'] = calculate_score(line)

        # Sort and Prune
        sup = sorted(self.get_support(), reverse=True, key=lambda k: k['score'])
        sup = sup[:best]
        res = sorted(self.get_resistance(), reverse=True, key=lambda k: k['score'])
        res = res[:best]
        self.lines = res + sup

        for line in self.get_resistance():
            line = f'Res: ssr={line["ssr"]:.1e}, '\
                        f'se={line["slope_err"]:.1e}, '\
                        f'ie={line["intercept_err"]:.1e}, '\
                        f'a={line["area_avg"]:.3f}, '\
                        f'd={line["dates"]}, '\
                        f's={line["score"]:.1e}, '\
                        f'x={line["end_point"]:.2f} '
            logger.debug(line)

        for line in self.get_support():
            line = f'Sup: ssr={line["ssr"]:.1e}, '\
                        f'se={line["slope_err"]:.1e}, '\
                        f'ie={line["intercept_err"]:.1e}, '\
                        f'a={line["area_avg"]:.3f}, '\
                        f'd={line["dates"]}, '\
                        f's={line["score"]:.1e}, '\
                        f'x={line["end_point"]:.2f} '
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