import matplotlib.pyplot as plt
import datetime as dt

import pandas as pd
import numpy as np

from base import Threaded
from data import store as store
from utils import ui, logger

_logger = logger.get_logger()


class Charts(Threaded):
    figure: plt.Figure
    ax: plt.Axes
    ticker: str
    history: pd.DataFrame

    def __init__(self, ticker: str, days: int = 365):
        if not store.is_ticker(ticker):
            raise ValueError(f'Ticker {ticker} is invalid')
        if days <= 10:
            raise ValueError(f'Days must be greater than 10')

        self.ticker = ticker.upper()
        self.days = days
        self.history = pd.DataFrame()
        self.company = {}
        self.figure, self.ax = plt.subplots(figsize=ui.CHART_SIZE)

        plt.style.use(ui.CHART_STYLE)
        plt.margins(x=0.1)
        plt.subplots_adjust(bottom=0.15)

        self.figure.canvas.manager.set_window_title(f'{self.ticker}')

    @Threaded.threaded
    def fetch_history(self):
        self.task_state = 'None'

        _logger.info(f'{__name__}: Fetching history for {self.ticker}...')

        self.task_ticker = self.ticker
        self.history = store.get_history(self.ticker, days=self.days)
        self.company = store.get_company(self.ticker)

        self.task_state = 'Done'

    def plot_history(self) -> plt.Figure:
        if self.history.empty:
            _logger.info(f'{__name__}: Need history for {self.ticker}. Fetching...')
            self.fetch_history()

        self.ax.secondary_yaxis('right')
        self.ax.set_title(f'{self.company["name"]}')

        if self.history.iloc[-1]['close'] < 30.0:
            self.ax.yaxis.set_major_formatter('{x:.2f}')
        else:
            self.ax.yaxis.set_major_formatter('{x:.0f}')

        length = len(self.history)
        dates = [self.history.iloc[index]['date'].strftime(ui.DATE_FORMAT) for index in range(length)]

        # Grid and ticks
        self.ax.grid(which='major', axis='both')
        self.ax.set_xticks(range(0, length+1, int(length/12)))
        self.ax.tick_params(axis='x', labelrotation=45)

        # Plot Highs & Lows using simple lines
        self.ax.plot(dates, self.history['high'], '-g', linewidth=0.5)
        self.ax.plot(dates, self.history['low'], '-r', linewidth=0.5)
        self.ax.fill_between(dates, self.history['high'], self.history['low'], facecolor='gray', alpha=0.4)

        return self.figure

    def plot_ohlc(self) -> plt.Figure:
        if self.history.empty:
            _logger.info(f'{__name__}: Need history for {self.ticker}. Fetching...')
            self.fetch_history()

        self.ax.secondary_yaxis('right')
        self.ax.set_title(f'{self.company["name"]}')

        if self.history.iloc[-1]['close'] < 30.0:
            self.ax.yaxis.set_major_formatter('{x:.2f}')
        else:
            self.ax.yaxis.set_major_formatter('{x:.0f}')

        # Grid
        self.ax.grid(which='major', axis='both')

        # Setup values
        width1 = 0.4
        width2 = 0.05
        interval = 5
        length = len(self.history)

        # Ticks
        ticks = self.history.index[::interval]
        self.ax.set_xticks(ticks)
        self.ax.tick_params(axis='x', labelrotation=45)
        labels = [self.history.iloc[i]['date'].strftime(ui.DATE_FORMAT) for i in range(0, length, interval)]
        self.ax.set_xticklabels(labels)

        # Find up and down days
        up = self.history[self.history['close'] >= self.history['open']].copy()
        dn = self.history[self.history['close'] < self.history['open']].copy()

        # Plot up prices
        self.ax.bar(up.index, up.high - up.close, width2, bottom=up.close, color='green')
        self.ax.bar(up.index, up.close - up.open, width1, bottom=up.open,  color='green')
        self.ax.bar(up.index, up.low - up.open,   width2, bottom=up.open,  color='green')

        # Plot down prices
        self.ax.bar(dn.index, dn.high - dn.open,  width2, bottom=dn.open,  color='red')
        self.ax.bar(dn.index, dn.close - dn.open, width1, bottom=dn.open,  color='red')
        self.ax.bar(dn.index, dn.low - dn.close,  width2, bottom=dn.close, color='red')

        return self.figure


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    logger.get_logger(logging.DEBUG)

    if len(sys.argv) > 1:
        chart = Charts(sys.argv[1])
        figure = chart.plot_ohlc()
    else:
        chart = Charts('IBM')
        chart.fetch_history()
        figure = chart.plot_ohlc()

    plt.figure(figure)
    plt.show()
