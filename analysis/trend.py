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

        output = f'score={self.score:.4f}, '\
                 f'width={self.width} '\
                 f'prox={self.proximity:.1f} '\
                 f'age={self.age} '\
                 f'end={self.end_point:.2f} '\
                 f'ssr={self.ssr:.1e}, '\
                 f'area={self.area_avg:.3f}, '\
                 f'dates={dates}'

        return output

    def calculate_score(self, price):
        self.proximity = abs(self.end_point - price)

        self.score = ((self.area_avg * self.width * len(self.points)) /
                     (self.age * self.proximity))

class SupportResistance:
    def __init__(self, ticker, start=None):
        if (validate_ticker(ticker)):
            self.ticker = ticker.upper()
            self.history = None
            self.price = 0.0
            self.lines = []
            self.extmethod = trendln.METHOD_NUMDIFF # METHOD_NAIVE, METHOD_NAIVECONSEC, METHOD_NUMDIFF*
            self.method = trendln.METHOD_NSQUREDLOGN # METHOD_NCUBED, METHOD_NSQUREDLOGN*, METHOD_HOUGHPOINTS, METHOD_HOUGHLINES, METHOD_PROBHOUGH

            if start is None:
                self.history = yf.Ticker(ticker).history(period="max", rounding=True)
            else:
                self.history = yf.Ticker(ticker).history(start=f'{start:%Y-%m-%d}', rounding=True)

            self.points = len(self.history)
            self.price = get_current_price(ticker)

            logger.debug(f'Initialized SupportResitance for {ticker} (${self.price:.2f})')
            logger.debug(f'{self.points} points from {self.history.iloc[0].name} to {self.history.iloc[-1].name}')
        else:
            logger.error('Error initializing SupportResitance')

    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'

    def calculate(self, best=5):
        if self.history is not None:
            self.lines = []

            # Calculate support and resistance lines
            maxs = trendln.calc_support_resistance((None, self.history.High), extmethod=self.extmethod, method=self.method, accuracy=2) #resistance
            mins = trendln.calc_support_resistance((self.history.Low, None), extmethod=self.extmethod, method=self.method, accuracy=2)  #support

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

                for point in line[0]:
                    newline.points += [{'index':point, 'date':''}]
                newline.width = newline.points[-1]['index'] - newline.points[0]['index']
                newline.age = self.points - newline.points[-1]['index']

                self.lines += [newline]

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

                for point in line[0]:
                    newline.points += [{'index':point, 'date':''}]
                newline.width = newline.points[-1]['index'] - newline.points[0]['index']
                newline.age = self.points - newline.points[-1]['index']

                self.lines += [newline]

            logger.info(f'{len(self.get_resistance())} total resistance lines')
            logger.info(f'{len(self.get_support())} total support lines')

            # Calculate dates of pivot points
            for line in self.lines:
                for point in line.points:
                    date = self.history.iloc[point['index']].name
                    point['date'] = [date.date().strftime('%Y-%m-%d')]

            # Calculate end point extension
            for line in self.lines:
                line.end_point = (self.points * line.slope) + line.intercept

            # Calculate final score
            for line in self.lines:
                line.calculate_score(self.price)

            # Sort and Prune
            sup = sorted(self.get_support(), reverse=True, key=lambda l: l.score)
            sup = sup[:best]
            res = sorted(self.get_resistance(), reverse=True, key=lambda l: l.score)
            res = res[:best]
            self.lines = res + sup

            for line in self.get_resistance():
                line = f'Res:{line}'
                logger.debug(line)

            for line in self.get_support():
                line = f'Sup:{line}'
                logger.debug(line)

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

    def get_endpoints(self):
        support = resistance = []
        for line in self.lines:
            if line.support:
                support += [line.end_point]
            else:
                resistance += [line.end_point]

        return support, resistance

    def plot(self, file=''):
        fig, ax = plt.subplots()
        plt.style.use('seaborn-pastel')
        plt.title(f'{self.ticker} History with Support & Resistance Lines')
        # ax.set_xlabel('Date')
        # ax.set_ylabel('Price')
        if self.price > 20.0:
            ax.yaxis.set_major_formatter('${x:.0f}')
        else:
            ax.yaxis.set_major_formatter('${x:.2f}')

        # High/Lows
        dates = []
        length = len(self.history)
        for index in range(length):
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]

        plt.xticks(range(0, length+1, int(length/12)))
        plt.xticks(rotation=45)
        plt.subplots_adjust(bottom=0.20)

        ax.plot(dates, self.history.High, '-g', label='High Price', linewidth=0.5)
        ax.plot(dates, self.history.Low, '-r', label='Low Price', linewidth=0.5)

        # Pivot points
        dates = []
        values = []
        for line in self.get_resistance():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].High]
        ax.plot(dates, values, '.g')

        dates = []
        values = []
        for line in self.get_support():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].Low]
        ax.plot(dates, values, '.r')

        # Trend lines
        dates = []
        values = []
        for line in self.get_resistance():
            index = line.points[0]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].High]
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.history.iloc[index].High]
            ax.plot(dates, values, '-g', linewidth=0.5)

        dates = []
        values = []
        for line in self.get_support():
            index = line.points[0]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].Low]
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.history.iloc[index].Low]
            ax.plot(dates, values, '-r', linewidth=0.5)

        # Trend lines extensions
        dates = []
        values = []
        for line in self.get_resistance():
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].High]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [line.end_point]
            ax.plot(dates, values, '--g', linewidth=0.5)

        dates = []
        values = []
        for line in self.get_support():
            index = line.points[-1]['index']
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.history.iloc[index].Low]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [line.end_point]
            ax.plot(dates, values, '--r', linewidth=0.5)

        # Price line
        plt.axhline(y=self.price, color='black', linestyle='-', label='Current Price', linewidth=0.5)
        plt.grid()
        # ax.legend()

        # Save as PNG if desired
        if file:
            fig.savefig(file, dpi=150)
            logger.info(f'Saved plot as {file}')

        return fig

'''
'Solarize_Light2', '_classic_test_patch', 'bmh', 'classic', 'dark_background', 'fast',
'fivethirtyeight', 'ggplot', 'grayscale', 'seaborn', 'seaborn-bright', 'seaborn-colorblind',
'seaborn-dark', 'seaborn-dark-palette', 'seaborn-darkgrid', 'seaborn-deep', 'seaborn-muted',
'seaborn-notebook', 'seaborn-paper', 'seaborn-pastel', 'seaborn-poster', 'seaborn-talk',
'seaborn-ticks', 'seaborn-white', 'seaborn-whitegrid', 'tableau-colorblind10'
'''

if __name__ == '__main__':
    import logging
    u.get_logger(logging.INFO)

    start = datetime.datetime.today() - datetime.timedelta(days=240)
    sr = SupportResistance('IBM', start=start)
    sr.calculate()
    sr.plot(file='plot.png')

    # fig = trendln.plot_support_resistance((None, sr.history.High), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], None), accuracy=2)
    # fig = trendln.plot_support_resistance((sr.history.Low[-300:], sr.history[-300:].High), accuracy=2)
    # fig.savefig('figure')
