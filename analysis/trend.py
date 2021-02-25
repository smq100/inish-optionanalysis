'''
    trendln: https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
             https://github.com/GregoryMorse/trendln
'''

import datetime

import yfinance as yf
import trendln
import numpy as np
import matplotlib.pyplot as plt

from pricing.fetcher import validate_ticker, get_current_price
from utils import utils as u

logger = u.get_logger()


class Line:
    def __init__(self):
        self.support = False
        self.rank = 0
        self.score = 0.0
        self.end_point = 0.0
        self.points = []
        self.slope = 0.0
        self.intercept = 0.0
        self.ssr = 0.0
        self.slope_err = 0.0
        self.intercept_err = 0.0
        self.area_avg = 0.0
        self.width = 0.0
        self.age = 0.0
        self.proximity = 0.0

    def __str__(self):
        dates = []
        for point in self.points:
            dates += point['date']

        output = f'score={self.score:.2f}, '\
                 f'rank={self.rank} '\
                 f'points={len(dates)} '\
                 f'width={self.width} '\
                 f'prox={self.proximity:.1f} '\
                 f'age={self.age} '\
                 f'end={self.end_point:.2f} '\
                 f'ssr={self.ssr:.1e}, '\
                 f'area={self.area_avg:.3f}'

        return output

    def calculate_score(self, price):
        self.proximity = abs(self.end_point - price)
        self.score = (self.width * len(self.points)) / (self.proximity * self.rank)

class SupportResistance:
    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.start = start
            self.history = None
            self.price = 0.0
            self.lines = []
            self.slope_sup = 0.0
            self.intercept_sup = 0.0
            self.slope_res = 0.0
            self.intercept_res = 0.0
            self.extmethod = trendln.METHOD_NUMDIFF # METHOD_NAIVE, METHOD_NAIVECONSEC, METHOD_NUMDIFF*
            self.method = trendln.METHOD_NSQUREDLOGN # METHOD_NCUBED, METHOD_NSQUREDLOGN*, METHOD_HOUGHPOINTS, METHOD_HOUGHLINES, METHOD_PROBHOUGH
        else:
            logger.error('{__name__}: Error initializing {__class__}')

    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'

    def calculate(self):
        self.lines = []

        if self.start is None:
            self.history = yf.Ticker(self.ticker).history(period="max", rounding=True)
        else:
            self.history = yf.Ticker(self.ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

        self.points = len(self.history)
        self.price = get_current_price(self.ticker)

        logger.info(f'{__name__}: {self.points} pivot points identified from {self.history.iloc[0].name} to {self.history.iloc[-1].name}')

        # Calculate support and resistance lines
        maxs = trendln.calc_support_resistance((None, self.history.High), extmethod=self.extmethod, method=self.method, accuracy=2) #resistance
        mins = trendln.calc_support_resistance((self.history.Low, None), extmethod=self.extmethod, method=self.method, accuracy=2)  #support

        maximaIdxs, pmax, maxtrend, maxwindows = maxs
        minimaIdxs, pmin, mintrend, minwindows = mins

        self.slope_res = pmax[0]
        self.intercept_res = pmax[1]

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

            for point in line[0]:
                newline.points += [{'index':point, 'date':''}]
            newline.width = newline.points[-1]['index'] - newline.points[0]['index']
            newline.age = self.points - newline.points[-1]['index']

            self.lines += [newline]

        self.slope_sup = pmin[0]
        self.intercept_sup = pmin[1]

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

            for point in line[0]:
                newline.points += [{'index':point, 'date':''}]
            newline.width = newline.points[-1]['index'] - newline.points[0]['index']
            newline.age = self.points - newline.points[-1]['index']

            self.lines += [newline]

        # Calculate dates of pivot points
        for line in self.lines:
            for point in line.points:
                date = self.history.iloc[point['index']].name
                point['date'] = [date.date().strftime('%Y-%m-%d')]

        # Calculate end point extension (y = mx + b)
        for line in self.lines:
            line.end_point = (self.points * line.slope) + line.intercept

        # Sort lines based on mathematical fit (ssr) and set the line ranking
        self.lines = sorted(self.lines, key=lambda l: l.ssr)
        for index, line in enumerate(self.lines):
            line.rank = index + 1

        # Calculate scores
        max_ = 0.0
        for line in self.lines:
            line.calculate_score(self.price)
            if line.score > max_:
                max_ = line.score

        # Normalize scores to a max of 10.0
        for line in self.lines:
            line.score /= max_
            line.score *= 10.0

        # Log the line details
        countr = counts = 0
        for line in self.lines:
            if line.support:
                counts += 1
            else:
                countr += 1

        logger.info(f'{__name__}: {countr} resistance lines identified')
        for line in self.get_resistance():
            line = f'{__name__}: Res:{line}'
            logger.debug(line)

        logger.info(f'{__name__}: {counts} support lines identified')
        for line in self.get_support():
            line = f'{__name__}: Sup:{line}'
            logger.debug(line)

    def get_resistance(self, best=5):
        if best < 1:
            raise AssertionError("'best' value must be >= 1")

        res = []
        for line in self.lines:
            if not line.support:
                res += [line]

        resistance = sorted(res, reverse=True, key=lambda l: l.score)

        return resistance[:best]

    def get_support(self, best=5):
        if best < 1:
            raise AssertionError("'best' value must be >= 1")

        sup = []
        for line in self.lines:
            if line.support:
                sup += [line]

        support = sorted(sup, reverse=True, key=lambda l: l.score)

        return support[:best]

    def plot(self, best=5, show=True, filename='', legend=True, srlines=False, trendlines=True):
        if best < 1:
            raise AssertionError("'best' value must be >= 1")

        fig, ax = plt.subplots()
        plt.style.use('seaborn')
        plt.grid()
        plt.title(f'{self.ticker} History with Support & Resistance')

        if self.price < 30.0:
            ax.yaxis.set_major_formatter('${x:.2f}')
        else:
            ax.yaxis.set_major_formatter('${x:.0f}')

        # High & Lows
        dates = []
        length = len(self.history)
        for index in range(length):
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]

        plt.xticks(range(0, length+1, int(length/12)))
        plt.xticks(rotation=45)
        plt.subplots_adjust(bottom=0.15)

        ax.plot(dates, self.history.High, '-g', label='High Price', linewidth=0.5)
        ax.plot(dates, self.history.Low, '-r', label='Low Price', linewidth=0.5)

        # Pivot points
        dates = []
        values = []
        for line in self.get_resistance(best=best):
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].High]
        ax.plot(dates, values, '.g')

        dates = []
        values = []
        for line in self.get_support(best=best):
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].Low]
        ax.plot(dates, values, '.r')

        # Trend lines
        dates = []
        values = []
        for line in self.get_resistance(best=best):
            index = line.points[0]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].High]
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.history.iloc[index].High]

            width = line.score / 5.0
            if width < 0.5: width = 0.5
            ax.plot(dates, values, '-g', linewidth=width)

        dates = []
        values = []
        for line in self.get_support(best=best):
            index = line.points[0]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].Low]
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.history.iloc[index].Low]

            width = line.score / 5.0
            if width < 0.5: width = 0.5
            ax.plot(dates, values, '-r', linewidth=width)

        # Trend line extensions
        dates = []
        values = []
        for line in self.get_resistance(best=best):
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].High]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [line.end_point]

            width = line.score / 5.0
            if width < 0.5: width = 0.5
            ax.plot(dates, values, ':g', linewidth=width)

        dates = []
        values = []
        for line in self.get_support(best=best):
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].Low]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [line.end_point]

            width = line.score / 5.0
            if width < 0.5: width = 0.5
            ax.plot(dates, values, ':r', linewidth=width)

        # Price line
        plt.axhline(y=self.price, color='b', linestyle='--', label='Current Price', linewidth=1.0)

        # Current support and resistance levels
        if srlines:
            for line in self.get_support(best=best):
                width = line.score / 5.0
                if width < 0.5: width = 0.5
                plt.axhline(y=line.end_point, color='r', linestyle='-', linewidth=width)

            for line in self.get_resistance(best=best):
                width = line.score / 5.0
                if width < 0.5: width = 0.5
                plt.axhline(y=line.end_point, color='g', linestyle='-', linewidth=width)

        if trendlines:
            index = 0
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.intercept_res]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.slope_res * self.points + self.intercept_res]

            ax.plot(dates, values, '-', color='darkgreen', label='Avg Res', linewidth=2.0)

            index = 0
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.intercept_sup]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.slope_sup * self.points + self.intercept_sup]

            ax.plot(dates, values, '-', color='darkred', label='Avg Sup', linewidth=2.0)

        if legend:
            plt.legend()

        if filename:
            fig.savefig(filename, dpi=150)
            logger.info(f'{__name__}: Saved plot as {filename}')

        if show:
            plt.show()

        return fig


if __name__ == '__main__':
    import sys
    import logging
    u.get_logger(logging.DEBUG)

    start = datetime.datetime.today() - datetime.timedelta(days=1000)
    if len(sys.argv) > 1:
        sr = SupportResistance(sys.argv[1], start=start)
    else:
        sr = SupportResistance('IBM', start=start)

    sr.calculate()
    sr.plot()
