'''
trendln: https://github.com/GregoryMorse/trendln
         https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
'''

import datetime

import yfinance as yf
import trendln
import matplotlib.pyplot as plt

from data import store as store
from utils import utils as utils

_logger = utils.get_logger()


class Line:
    def __init__(self):
        self.support = False
        self.fit = 0
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

        class Score:
            self.fit = 0.0
            self.width = 0.0
            self.proximity = 0.0
            self.points = 0.0

        self.score = Score()

    def get_score(self):
        score = (
            (self.score.fit *       0.20) +
            (self.score.width *     0.20) +
            (self.score.proximity * 0.20) +
            (self.score.points *    0.30) +
            (self.score.age *       0.10))

        return score

    def __str__(self):
        dates = []
        for point in self.points:
            dates += point['date']

        output = f'score={self.get_score():.2f}, '\
                 f'fit={self.fit:4n} '\
                 f'*fit={self.score.fit:5.2f} '\
                 f'wid={self.width:4n} '\
                 f'*wid={self.score.width:5.2f} '\
                 f'prox={self.proximity:5.1f} '\
                 f'*prox={self.score.proximity:5.2f} '\
                 f'pnts={len(dates)} '\
                 f'*pnts={self.score.points:5.2f} '\
                 f'age={self.age:4n} '\
                 f'*age={self.score.age:5.2f}'

        return output

class SupportResistance:
    def __init__(self, ticker, best=5, start=None):
        if best < 1:
            raise AssertionError("'best' value must be > 0")

        if (store.is_symbol_valid(ticker)):
            self.ticker = ticker.upper()
            self.best = best
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
            _logger.error('{__name__}: Error initializing {__class__}')

    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'

    def calculate(self):
        self.lines = []

        if self.start is None:
            self.history = yf.Ticker(self.ticker).history(period="max", rounding=True)
        else:
            self.history = yf.Ticker(self.ticker).history(start=f'{self.start:%Y-%m-%d}', rounding=True)

        self.points = len(self.history)
        self.price = store.get_current_price(self.ticker)

        _logger.info(f'{__name__}: {self.points} pivot points identified from {self.history.iloc[0].name} to {self.history.iloc[-1].name}')

        # Calculate support and resistance lines
        maxs = trendln.calc_support_resistance((None, self.history.High), extmethod=self.extmethod, method=self.method, accuracy=8) #resistance
        mins = trendln.calc_support_resistance((self.history.Low, None), extmethod=self.extmethod, method=self.method, accuracy=8)  #support

        maximaIdxs, pmax, maxtrend, maxwindows = maxs
        minimaIdxs, pmin, mintrend, minwindows = mins

        self.slope_res = pmax[0]
        self.intercept_res = pmax[1]

        for line in maxtrend:
            newline = Line()
            newline.support = False
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
            line.fit = index + 1

        # Normalize scoring criteria to 10.0 scale
        #    Rank
        max_ = 0.0
        for line in self.lines:
            if line.fit > max_: max_ = line.fit
        for line in self.lines:
            line.score.fit = line.fit / max_
            line.score.fit *= 10.0
            line.score.fit = 10.0 - line.score.fit # Lower is better

        #    Width
        max_ = 0.0
        for line in self.lines:
            if line.width > max_: max_ = line.width
        for line in self.lines:
            line.score.width = line.width / max_
            line.score.width *= 10.0

        #    Proximity
        max_ = 0.0
        for line in self.lines:
            line.proximity = abs(line.end_point - self.price)
            if line.proximity > max_: max_ = line.proximity
        for line in self.lines:
            line.score.proximity = line.proximity / max_
            line.score.proximity *= 10.0
            line.score.proximity = 10.0 - line.score.proximity # Lower is better

        #    Points
        max_ = 0.0
        for line in self.lines:
            if len(line.points) > max_: max_ = len(line.points)
        for line in self.lines:
            line.score.points = len(line.points) / max_
            line.score.points *= 10.0

        #    Age
        max_ = 0.0
        for line in self.lines:
            if line.age > max_: max_ = line.age
        for line in self.lines:
            line.score.age = line.age / max_
            line.score.age *= 10.0
            line.score.age = 10.0 - line.score.age # Lower is better

        # Sort lines based on total score
        self.lines = sorted(self.lines, reverse=True, key=lambda l: l.get_score())

        # Log the line details
        countr = counts = 0
        for line in self.lines:
            if line.support:
                counts += 1
            else:
                countr += 1

        _logger.info(f'{__name__}: {countr} resistance lines identified')
        for line in self.get_resistance():
            line = f'{__name__}: Res:{line}'
            _logger.debug(line)

        _logger.info(f'{__name__}: {counts} support lines identified')
        for line in self.get_support():
            line = f'{__name__}: Sup:{line}'
            _logger.debug(line)

    def get_resistance(self):
        res = []
        for line in self.lines:
            if not line.support:
                res += [line]

        resistance = sorted(res, reverse=True, key=lambda l: l.get_score())

        return resistance[:self.best]

    def get_support(self):
        sup = []
        for line in self.lines:
            if line.support:
                sup += [line]

        support = sorted(sup, reverse=True, key=lambda l: l.get_score())

        return support[:self.best]

    def plot(self, show=True, filename='', legend=True, srlines=False, trendlines=True):
        fig, ax1 = plt.subplots()
        ax2 = ax1.secondary_yaxis('right')
        plt.style.use('seaborn')
        plt.grid()
        plt.margins(x=0.1)
        plt.title(f'{self.ticker} History with Support & Resistance')
        width = 1.0

        if self.price < 30.0:
            ax1.yaxis.set_major_formatter('${x:.2f}')
            ax2.yaxis.set_major_formatter('${x:.2f}')
        else:
            ax1.yaxis.set_major_formatter('${x:.0f}')
            ax2.yaxis.set_major_formatter('${x:.0f}')

        # High & Lows
        dates = []
        length = len(self.history)
        for index in range(length):
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]

        plt.xticks(range(0, length+1, int(length/12)))
        plt.xticks(rotation=45)
        plt.subplots_adjust(bottom=0.15)

        ax1.plot(dates, self.history.High, '-g', linewidth=0.5)
        ax1.plot(dates, self.history.Low, '-r', linewidth=0.5)
        ax1.fill_between(dates, self.history.High, self.history.Low, facecolor='gray', alpha=0.4)

        # Pivot points
        dates = []
        values = []
        for line in self.get_resistance():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].High]
        ax1.plot(dates, values, '.g')

        dates = []
        values = []
        for line in self.get_support():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [self.history.iloc[index].Low]
        ax1.plot(dates, values, '.r')

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

            ax1.plot(dates, values, '-g', linewidth=width)

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

            ax1.plot(dates, values, '-r', linewidth=width)

        # Trend line extensions
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

            ax1.plot(dates, values, ':g', linewidth=width)

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

            ax1.plot(dates, values, ':r', linewidth=width)

        # End points
        text = []
        dates = []
        values = []
        for index, line in enumerate(self.get_resistance()):
            ep = utils.mround(line.end_point, 0.1)
            if ep not in values:
                date = self.history.iloc[-1].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [ep]
                text += [{'text':f'{line.end_point:.2f}:{index+1}', 'value':line.end_point, 'color':'green'}]
        ax1.plot(dates, values, '.g', marker='.')

        dates = []
        values = []
        for index, line in enumerate(self.get_support()):
            ep = utils.mround(line.end_point, 0.1)
            if ep not in values:
                date = self.history.iloc[-1].name
                dates += [date.date().strftime('%Y-%m-%d')]
                values += [ep]
                text += [{'text':f'{line.end_point:.2f}:{index+1}', 'value':line.end_point, 'color':'red'}]
        ax1.plot(dates, values, '.r', marker='.')

        # End point text
        ylimits = ax1.get_ylim()
        inc = (ylimits[1] - ylimits[0]) / 33.0
        text = sorted(text, key=lambda t: t['value'])
        index = 1
        for txt in text:
            if txt['value'] > self.price:
                ax1.text(self.points+5, self.price+(index*inc), txt['text'], color=txt['color'], va='center', size='small')
                index += 1

        text = sorted(text, reverse=True, key=lambda t: t['value'])
        index = 1
        for txt in text:
            if txt['value'] < self.price:
                ax1.text(self.points+5, self.price-(index*inc), txt['text'], color=txt['color'], va='center', size='small')
                index += 1

        # Price line
        ax1.hlines(self.price, 0, self.points, color='blue', linestyle='--', label='Current Price', linewidth=1.0)
        ax1.text(self.points+5, self.price, f'{self.price:.2f}', color='blue', va='center', size='small')

        # Current support and resistance levels
        if srlines:
            for line in self.get_support():
                plt.axhline(y=line.end_point, color='r', linestyle='-', linewidth=width)

            for line in self.get_resistance():
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

            ax1.plot(dates, values, '--', color='darkgreen', label='Avg Resistance', linewidth=1.7)

            index = 0
            date = self.history.iloc[index].name
            dates = [date.date().strftime('%Y-%m-%d')]
            values = [self.intercept_sup]
            index = self.points-1
            date = self.history.iloc[index].name
            dates += [date.date().strftime('%Y-%m-%d')]
            values += [self.slope_sup * self.points + self.intercept_sup]

            ax1.plot(dates, values, '--', color='darkred', label='Avg Support', linewidth=1.7)

        if legend:
            plt.legend()

        if filename:
            fig.savefig(filename, dpi=150)
            _logger.info(f'{__name__}: Saved plot as {filename}')

        if show:
            plt.show()

        return fig


if __name__ == '__main__':
    import sys
    # import logging
    # u.get_logger(logging.DEBUG)

    start = datetime.datetime.today() - datetime.timedelta(days=500)
    if len(sys.argv) > 1:
        sr = SupportResistance(sys.argv[1], best=5, start=start)
    else:
        sr = SupportResistance('IBM', best=5, start=start)

    sr.calculate()
    sr.plot()
