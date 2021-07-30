'''
trendln: https://github.com/GregoryMorse/trendln
         https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530,
'''

import matplotlib.pyplot as plt
import trendln

from data import store as store
from utils import utils as utils

_logger = utils.get_logger()

METHOD = {
    'NCUBED': (trendln.METHOD_NCUBED, 'NCUBED'),
    'NSQUREDLOGN': (trendln.METHOD_NSQUREDLOGN, 'NSQUREDLOGN'),
    'HOUGHPOINTS': (trendln.METHOD_HOUGHPOINTS, 'HOUGHPOINTS'),
    'HOUGHLINES': (trendln.METHOD_HOUGHLINES, 'HOUGHLINES'),
    'PROBHOUGH': (trendln.METHOD_PROBHOUGH, 'PROBHOUGH'),
}

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

    def get_score(self) -> float:
        score = (
            (self.score.fit *       0.20) +
            (self.score.width *     0.20) +
            (self.score.proximity * 0.20) +
            (self.score.points *    0.30) +
            (self.score.age *       0.10))

        return score

    def __str__(self):
        dates = [point['date'] for point in self.points]

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
    def __init__(self, ticker, method='NSQUREDLOGN', best=3, days=1000):
        if best < 1:
            raise AssertionError("'best' value must be > 0")

        if days <= 30:
            utils.print_error('Days must be greater than 30')

        elif (store.is_symbol_valid(ticker)):
            self.ticker = ticker.upper()
            self.method = METHOD[method]
            self.best = best
            self.days = days
            self.history = None
            self.price = 0.0
            self.extmethod = trendln.METHOD_NUMDIFF # Pivit point detection: METHOD_NAIVE, METHOD_NAIVECONSEC, *METHOD_NUMDIFF
            self.lines = []
            self.slope_sup = 0.0
            self.intercept_sup = 0.0
            self.slope_res = 0.0
            self.intercept_res = 0.0
            self.accuracy = 8
        else:
            _logger.error('{__name__}: Error initializing {__class__}')

    def __str__(self):
        return f'Support and resistance analysis for {self.ticker} (${self.price:.2f})'

    def calculate(self) -> None:
        self.history = store.get_history(self.ticker, self.days)
        if self.history is None:
            raise ValueError('Unable to get history')

        self.price = store.get_current_price(self.ticker)
        if self.price is None:
            raise ValueError('Unable to get price')

        self.points = len(self.history)
        _logger.info(f'{__name__}: {self.points} pivot points identified from {self.history.iloc[0]["date"]} to {self.history.iloc[-1]["date"]}')

        # Calculate support and resistance lines
        maxs = trendln.calc_support_resistance((None, self.history['high']), extmethod=self.extmethod, method=self.method[0], accuracy=self.accuracy)
        mins = trendln.calc_support_resistance((self.history['low'], None), extmethod=self.extmethod, method=self.method[0], accuracy=self.accuracy)

        maximaIdxs, pmax, maxtrend, maxwindows = maxs
        minimaIdxs, pmin, mintrend, minwindows = mins

        self.slope_res = pmax[0]
        self.intercept_res = pmax[1]

        self.lines = []
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

            newline.points = [{'index':point, 'date':''} for point in line[0]]
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

            newline.points = [{'index':point, 'date':''} for point in line[0]]
            newline.width = newline.points[-1]['index'] - newline.points[0]['index']
            newline.age = self.points - newline.points[-1]['index']

            self.lines += [newline]

        # Calculate dates of pivot points
        for line in self.lines:
            for point in line.points:
                date = self.history['date'].iloc[point['index']]
                point['date'] = [date.strftime('%Y-%m-%d')]

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

    def get_resistance(self) -> list[float]:
        res = [line for line in self.lines if not line.support]
        resistance = sorted(res, reverse=True, key=lambda l: l.get_score())

        return resistance[:self.best]

    def get_support(self) -> list[float]:
        sup = [line for line in self.lines if line.support]
        support = sorted(sup, reverse=True, key=lambda l: l.get_score())

        return support[:self.best]

    def plot(self, show:bool=True, filename:str='', legend:bool=True, srlines:bool=False, trendlines:bool=True) -> plt.Figure:
        fig, ax1 = plt.subplots(figsize=(17,10))
        ax2 = ax1.secondary_yaxis('right')
        # plt.style.use('seaborn')
        plt.grid()
        plt.margins(x=0.1)
        plt.title(f'{self.ticker} History with Support & Resistance ({self.method[1]})')
        fig.canvas.manager.set_window_title(f'{self.ticker} ({self.method[1]})')
        line_width = 1.0

        if self.price < 30.0:
            ax1.yaxis.set_major_formatter('${x:.2f}')
            ax2.yaxis.set_major_formatter('${x:.2f}')
        else:
            ax1.yaxis.set_major_formatter('${x:.0f}')
            ax2.yaxis.set_major_formatter('${x:.0f}')

        # Highs & Lows
        length = len(self.history)
        dates = [self.history.iloc[index]['date'].strftime('%Y-%m-%d') for index in range(length)]

        plt.xticks(range(0, length+1, int(length/12)))
        plt.xticks(rotation=45)
        plt.subplots_adjust(bottom=0.15)

        ax1.plot(dates, self.history['high'], '-g', linewidth=0.5)
        ax1.plot(dates, self.history['low'], '-r', linewidth=0.5)
        ax1.fill_between(dates, self.history['high'], self.history['low'], facecolor='gray', alpha=0.4)

        # Pivot points
        dates = []
        values = []
        for line in self.get_resistance():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index]['date']
                dates += [date.strftime('%Y-%m-%d')]
                values += [self.history.iloc[index]['high']]
        ax1.plot(dates, values, '.g')

        dates = []
        values = []
        for line in self.get_support():
            for point in line.points:
                index = point['index']
                date = self.history.iloc[index]['date']
                dates += [date.strftime('%Y-%m-%d')]
                values += [self.history.iloc[index]['low']]
        ax1.plot(dates, values, '.r')

        # Trend lines
        dates = []
        values = []
        for line in self.get_resistance():
            index = line.points[0]['index']
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.history.iloc[index]['high']]
            index = line.points[-1]['index']
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
            values += [self.history.iloc[index]['high']]

            ax1.plot(dates, values, '-g', linewidth=line_width)

        dates = []
        values = []
        for line in self.get_support():
            index = line.points[0]['index']
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.history.iloc[index]['low']]
            index = line.points[-1]['index']
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
            values += [self.history.iloc[index]['low']]

            ax1.plot(dates, values, '-r', linewidth=line_width)

        # Trend line extensions
        dates = []
        values = []
        for line in self.get_resistance():
            index = line.points[-1]['index']
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.history.iloc[index]['high']]
            index = self.points-1
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
            values += [line.end_point]

            ax1.plot(dates, values, ':g', linewidth=line_width)

        dates = []
        values = []
        for line in self.get_support():
            index = line.points[-1]['index']
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.history.iloc[index]['low']]
            index = self.points-1
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
            values += [line.end_point]

            ax1.plot(dates, values, ':r', linewidth=line_width)

        # End points
        text = []
        dates = []
        values = []
        for index, line in enumerate(self.get_resistance()):
            ep = utils.mround(line.end_point, 0.1)
            if ep not in values:
                date = self.history['date'].iloc[-1]
                dates += [date.strftime('%Y-%m-%d')]
                values += [ep]
                text += [{'text':f'{line.end_point:.2f}:{index+1}', 'value':line.end_point, 'color':'green'}]
        ax1.plot(dates, values, '.g')

        dates = []
        values = []
        for index, line in enumerate(self.get_support()):
            ep = utils.mround(line.end_point, 0.1)
            if ep not in values:
                date = self.history['date'].iloc[-1]
                dates += [date.strftime('%Y-%m-%d')]
                values += [ep]
                text += [{'text':f'{line.end_point:.2f}:{index+1}', 'value':line.end_point, 'color':'red'}]
        ax1.plot(dates, values, '.r')

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
                plt.axhline(y=line.end_point, color='r', linestyle='-', linewidth=line_width)

            for line in self.get_resistance():
                plt.axhline(y=line.end_point, color='g', linestyle='-', linewidth=line_width)

        if trendlines:
            index = 0
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.intercept_res]
            index = self.points-1
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
            values += [self.slope_res * self.points + self.intercept_res]

            ax1.plot(dates, values, '--', color='darkgreen', label='Avg Resistance', linewidth=1.7)

            index = 0
            date = self.history.iloc[index]['date']
            dates = [date.strftime('%Y-%m-%d')]
            values = [self.intercept_sup]
            index = self.points-1
            date = self.history.iloc[index]['date']
            dates += [date.strftime('%Y-%m-%d')]
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

    if len(sys.argv) > 1:
        sr = SupportResistance(sys.argv[1], best=5)
    else:
        sr = SupportResistance('IBM', best=5)

    try:
        sr.calculate()
    except:
        raise ValueError('Unable to calculate')
    else:
        sr.plot()
