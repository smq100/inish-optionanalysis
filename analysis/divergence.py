from dataclasses import dataclass

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from ta import trend
from sklearn.preprocessing import MinMaxScaler

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, logger


_logger = logger.get_logger()


class Divergence(Threaded):
    def __init__(self, ticker: str, window: int = 15, days: int = 100):
        self.ticker: str = ticker
        self.window: int = window
        self.days: int = days
        self.results: pd.DataFrame = pd.DataFrame()
        self.history: pd.DataFrame = pd.DataFrame()
        self.divergence: pd.Series = pd.Series(dtype=float)
        self.divergence_only: pd.Series = pd.Series(dtype=float)
        self.type: str = 'rsi'
        self.interval: int = 14
        self.periods: int = 3

        if (store.is_ticker(ticker)):
            self.ticker = ticker
        else:
            raise ValueError('{__name__}: Error initializing {__class__} with ticker {ticker}')

    def calculate(self) -> pd.DataFrame:
        ta = Technical(self.ticker, None, self.days)
        self.history = ta.history
        scaler = MinMaxScaler(feature_range=(0, 1))

        # Calculate 0-1 scaled series of day-to-day price differences
        dates = self.history['date'][self.interval:].reset_index(drop=True)
        price = self.history['close'][self.interval:].reset_index(drop=True)
        price.name = 'price'
        price_sma = trend.sma_indicator(price, window=self.window, fillna=True).reset_index(drop=True)
        price_sma.name = 'price_sma'
        price_sma_diff = price_sma.diff(periods=self.periods).fillna(0.0)
        price_sma_diff.name = 'price_sma_diff'
        scaled = scaler.fit_transform(price_sma.values.reshape(-1, 1))
        scaled = [value[0] for value in scaled]
        price_sma_scaled = pd.Series(scaled)
        price_sma_scaled.name = 'price_sma_scaled'
        price_sma_scaled_diff = price_sma_scaled.diff(periods=self.periods).fillna(0.0)
        price_sma_scaled_diff.name = 'price_sma_scaled_diff'

        # Calculate 0-1 scaled series of day-to-day rsi differences
        technical = ta.calc_rsi(self.interval)[self.interval:]
        technical_sma = trend.sma_indicator(technical, window=self.window, fillna=True).reset_index(drop=True)
        technical_sma.name = f'{self.type}_sma'
        technical_sma_diff = technical_sma.diff(periods=self.periods).fillna(0.0)
        technical_sma_diff.name = f'{self.type}_sma_diff'
        scaled = scaler.fit_transform(technical_sma.values.reshape(-1, 1))
        scaled = [value[0] for value in scaled]
        technical_sma_scaled = pd.Series(scaled)
        technical_sma_scaled.name = f'{self.type}_sma_scaled'
        technical_sma_scaled_diff = technical_sma_scaled.diff(periods=self.periods).fillna(0.0)
        technical_sma_scaled_diff.name = f'{self.type}_sma_scaled_diff'

        # Calculate differences in the slopes between prices and RSI's
        self.divergence = price_sma_scaled_diff - technical_sma_scaled_diff
        self.divergence.name = 'div'

        # Calculate differences in the slopes between prices and RSI's for opposite slopes only
        div = []
        for i in range(len(price_sma_scaled_diff)):
            p = price_sma_scaled_diff[i]
            t = technical_sma_scaled_diff[i]
            div += [p - t if p * t < 0.0 else np.NaN]
        self.divergence_only = pd.Series(div)
        self.divergence_only.name = 'divHL'

        # Overall dataframe
        self.results = dates
        self.results = pd.concat([self.results, price], axis=1)
        self.results = pd.concat([self.results, price_sma], axis=1)
        self.results = pd.concat([self.results, price_sma_diff], axis=1)
        self.results = pd.concat([self.results, price_sma_scaled], axis=1)
        self.results = pd.concat([self.results, price_sma_scaled_diff], axis=1)

        tech = technical.reset_index(drop=True)
        self.results = pd.concat([self.results, tech], axis=1)
        self.results = pd.concat([self.results, technical_sma], axis=1)
        self.results = pd.concat([self.results, technical_sma_diff], axis=1)
        self.results = pd.concat([self.results, technical_sma_scaled], axis=1)
        self.results = pd.concat([self.results, technical_sma_scaled_diff], axis=1)

        self.results = pd.concat([self.results, self.divergence], axis=1)
        self.results = pd.concat([self.results, self.divergence_only], axis=1)

        return self.results.copy()

    def plot(self, show: bool = True, cursor: bool = True) -> plt.Figure:
        if len(self.results) == 0:
            raise ValueError('Must first run calculate()')

        axes: list[plt.Axes]
        figure: plt.Figure
        figure, axes = plt.subplots(nrows=3, figsize=ui.CHART_SIZE, sharex=True)

        plt.style.use(ui.CHART_STYLE)
        plt.margins(x=0.1)
        plt.subplots_adjust(bottom=0.15)

        figure.canvas.manager.set_window_title(self.ticker)
        axes[0].set_title('Price')
        axes[1].set_title(self.type.upper())
        axes[2].set_title('Divergence')

        # Grid and ticks
        length = len(self.results)
        axes[0].grid(which='major', axis='both')
        axes[0].set_xticks(range(0, length+1, length//10))
        axes[1].grid(which='major', axis='both')
        axes[1].set_xticks(range(0, length+1, length//10))
        axes[1].set_ylim([-5, 105])
        axes[2].grid(which='major', axis='both')
        axes[2].tick_params(axis='x', labelrotation=45)

        # Plot
        dates = [self.results.iloc[index]['date'].strftime(ui.DATE_FORMAT2) for index in range(length)]
        axes[0].plot(dates, self.results['price'], '-', color='blue', label='Price', linewidth=0.5)
        axes[0].plot(dates, self.results['price_sma'], '-', color='orange', label=f'SMA{self.interval}', linewidth=1.5)
        axes[1].plot(dates, self.results['rsi'], '-', color='blue', label=self.type.upper(), linewidth=0.5)
        axes[1].plot(dates, self.results['rsi_sma'], '-', color='orange', label=f'SMA{self.interval}', linewidth=1.5)
        axes[2].plot(dates[self.periods:], self.results['div'][self.periods:], '-', color='orange', label='Div', linewidth=1.0)
        axes[2].plot(dates[self.periods:], self.results['divHL'][self.periods:], '-', color='green', label='DivHL', linewidth=1.0)
        axes[2].axhline(y=0.0, xmin=0, xmax=100, color='black', linewidth=1.5)

        # Price line limits
        min = self.results['price'].min()
        max = self.results['price'].max()
        axes[0].set_ylim([min*0.95, max*1.05])

        # Legend
        axes[0].legend(loc='best')
        axes[1].legend(loc='best')

        if cursor:
            cursor = self.custom_cursor(axes, data=self.results)
            figure.canvas.mpl_connect('motion_notify_event', cursor.show_xy)
            figure.canvas.mpl_connect('axes_leave_event', cursor.hide_y)

        if show:
            plt.figure(figure)
            plt.show()

        return figure

    class custom_cursor(object):
        def __init__(self, axes: list[plt.Axes], data: pd.DataFrame, showy: bool = True):
            self.items = np.zeros(shape=(len(axes), 4), dtype=object)
            self.data = data
            self.showy = showy
            self.focus = 0

            for i, ax in enumerate(axes):
                ax.set_gid(i)
                lx = ax.axvline(ymin=0, ymax=100, color='k', linewidth=0.5)
                ly = ax.axhline(xmin=0, xmax=100, color='k', linewidth=0.5)
                props = dict(boxstyle='round', fc='linen', alpha=0.4)
                an = ax.annotate('', xy=(0, 0), xytext=(-20, 20), textcoords='offset points', bbox=props)
                an.set_visible(False)
                item = [ax, lx, ly, an]
                self.items[i] = item

        def show_xy(self, event):
            if event.inaxes:
                self.focus = event.inaxes.get_gid()

                ax: plt.Axes
                for ax in self.items[:, 0]:
                    self.gid = ax.get_gid()
                    for lx in self.items[:, 1]:
                        lx.set_xdata(event.xdata)

                    if self.showy and (self.focus == ax.get_gid()):
                        ln = self.items[self.gid, 2]
                        ln.set_ydata(event.ydata)
                        ln.set_visible(True)
                        an = self.items[self.gid, 3]
                        an.set_visible(True)

                    x = event.xdata
                    y = event.ydata
                    if x >= 0 and x < len(self.data):
                        an = self.items[self.gid, 3]
                        an.xy = (x, y)

                        if self.focus == 0:
                            text = f'{self.data.iloc[int(x)]["price"]:.2f} ({self.data.iloc[int(x)]["price_sma"]:.2f} / {self.data.iloc[int(x)]["price_sma_diff"]:.2f})'
                        elif self.focus == 1:
                            text = f'{self.data.iloc[int(x)]["rsi"]:.2f} ({self.data.iloc[int(x)]["rsi_sma"]:.2f} / {self.data.iloc[int(x)]["rsi_sma_diff"]:.2f})'
                        else:
                            text = ''
                        an.set_text(text)

            plt.draw()

        def hide_y(self, event):
            for ax in self.items[:, 0]:
                if self.focus == ax.get_gid():
                    self.items[self.focus, 2].set_visible(False)
                    self.items[self.focus, 3].set_visible(False)


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    # logger.get_logger(logging.DEBUG)

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'IBM'
    div = Divergence(ticker)
    div.calculate()
    div.plot()
