import matplotlib.pyplot as plt

import pandas as pd

from base import Threaded
from data import store as store
from utils import ui, logger

_logger = logger.get_logger()


class Charts(Threaded):
    figure: plt.Figure
    ax: plt.Axes
    ticker: str
    history: pd.DataFrame

    def __init__(self):
        self.ticker = ''
        self.history = pd.DataFrame()
        self.company = {}
        self.figure, self.ax = plt.subplots(figsize=(17, 10))

    @Threaded.threaded
    def fetch_history(self, ticker: str):
        self.task_state = 'None'

        if store.is_ticker(ticker):
            _logger.info(f'{__name__}: Fetching history for {self.ticker}...')

            self.ticker = ticker
            self.task_ticker = ticker
            self.history = store.get_history(ticker, 1000)
            self.company = store.get_company(self.ticker)

        else:
            _logger.error(f'{__name__}: Ticker {ticker} is not valid')

        self.task_state = 'Done'

    def plot_history(self, ticker: str = '') -> plt.Figure:
        if not ticker and not self.ticker:
            raise AssertionError('Supply ticker symbol or first obtain price history using Charts.get_history()')

        if not ticker:
            pass # use prior self.ticker
        elif ticker != self.ticker:
            if store.is_ticker(ticker):
                self.ticker = ticker.upper()
                self.history = pd.DataFrame()
                self.figure, self.ax = plt.subplots(figsize=(17, 10))

        if self.history.empty:
            _logger.info(f'{__name__}: Need history for {self.ticker}. Fetching...')
            self.fetch_history(self.ticker)

        plt.style.use(ui.CHART_STYLE)
        plt.grid()
        plt.margins(x=0.1)

        self.figure.canvas.manager.set_window_title(f'{ticker.upper()}')
        self.ax.secondary_yaxis('right')

        plt.title(f'{self.company["name"]}')

        if self.history.iloc[-1]['close'] < 30.0:
            self.ax.yaxis.set_major_formatter('{x:.2f}')
        else:
            self.ax.yaxis.set_major_formatter('{x:.0f}')

        # Plot Highs & Lows using simple lines
        length = len(self.history)
        dates = [self.history.iloc[index]['date'].strftime(ui.DATE_FORMAT) for index in range(length)]

        plt.xticks(range(0, length+1, int(length/12)))
        plt.xticks(rotation=45)
        plt.subplots_adjust(bottom=0.15)

        self.ax.plot(dates, self.history['high'], '-g', linewidth=0.5)
        self.ax.plot(dates, self.history['low'], '-r', linewidth=0.5)
        self.ax.fill_between(dates, self.history['high'], self.history['low'], facecolor='gray', alpha=0.4)

        return self.figure


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    logger.get_logger(logging.DEBUG)

    chart = Charts()
    if len(sys.argv) > 1:
        figure = chart.plot_history(sys.argv[1])
    else:
        chart.fetch_history('AAPL')
        figure = chart.plot_history()

    plt.figure(figure)
    plt.show()
