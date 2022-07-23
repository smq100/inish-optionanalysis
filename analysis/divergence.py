from dataclasses import dataclass

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta import trend
from sklearn.preprocessing import MinMaxScaler

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, logger


_logger = logger.get_logger()


@dataclass
class _Data:
    interval: int = 14
    periods: int = 5
    data: pd.DataFrame = pd.DataFrame()
    data_sma: pd.Series = pd.Series(dtype=float)
    data_sma_scaled: pd.Series = pd.Series(dtype=float)
    data_sma_scaled_diff: pd.Series = pd.Series(dtype=float)


class Divergence(Threaded):
    def __init__(self, ticker: str, window: int = 15, days: int = 365):
        self.ticker = ''
        self.window = window
        self.days = days
        self.history = pd.DataFrame()
        self.price = _Data()
        self.technical = _Data()
        self.divergence = pd.Series(dtype=float)
        self.divergence_only = pd.Series(dtype=float)
        self.type = 'rsi'

        if (store.is_ticker(ticker)):
            self.ticker = ticker
        else:
            raise ValueError('{__name__}: Error initializing {__class__} with ticker {ticker}')

    @Threaded.threaded
    def calculate(self) -> None:
        ta = Technical(self.ticker, None, self.days)
        self.history = ta.history
        scaler = MinMaxScaler(feature_range=(0, 1))

        # Calculate 0-1 scaled series of day-to-day price differences
        self.price.data = self.history['close'][self.price.interval:]
        self.price.data_sma = trend.sma_indicator(self.price.data, window=self.window, fillna=True).reset_index(drop=True)
        scaled = scaler.fit_transform(self.price.data_sma.values.reshape(-1, 1))
        scaled = [value[0] for value in scaled]
        self.price.data_sma_scaled = pd.Series(scaled)
        self.price.data_sma_scaled_diff = self.price.data_sma_scaled.diff(periods=self.price.periods).fillna(0.0)

        # Calculate 0-1 scaled series of day-to-day rsi differences
        self.technical.data = ta.calc_rsi(self.technical.interval)[self.technical.interval:]
        self.technical.data_sma = trend.sma_indicator(self.technical.data, window=self.window, fillna=True).reset_index(drop=True)
        scaled = scaler.fit_transform(self.technical.data_sma.values.reshape(-1, 1))
        scaled = [value[0] for value in scaled]
        self.technical.data_sma_scaled = pd.Series(scaled)
        self.technical.data_sma_scaled_diff = self.technical.data_sma_scaled.diff(periods=self.technical.periods).fillna(0.0)

        # Calculate differences in the slopes between prices and RSI's
        self.divergence = self.price.data_sma_scaled_diff - self.technical.data_sma_scaled_diff

        # Calculate differences in the slopes between prices and RSI's for opposite slopes only
        div = []
        for i in range(len(self.price.data_sma_scaled_diff)):
            p = self.price.data_sma_scaled_diff[i]
            t = self.technical.data_sma_scaled_diff[i]
            div += [p - t if p * t < 0.0 else np.NaN]
        self.divergence_only = pd.Series(div)

    def plot(self, show: bool = True) -> plt.Figure:
        if len(self.price.data) == 0:
            raise ValueError('No price history. Run calculate()')
        if len(self.technical.data) == 0:
            raise ValueError('No technical history. Run calculate()')

        axs: list[plt.Axes]
        figure: plt.Figure
        figure, axs = plt.subplots(nrows=3, figsize=ui.CHART_SIZE, sharex=True)

        plt.style.use(ui.CHART_STYLE)
        plt.margins(x=0.1)
        plt.subplots_adjust(bottom=0.15)

        figure.canvas.manager.set_window_title(self.ticker)
        axs[0].set_title('Price')
        axs[1].set_title(self.type.upper())
        axs[2].set_title('Divergence')

        # Data
        data  = [self.price.data]
        data += [self.price.data_sma]
        data += [self.technical.data]
        data += [self.technical.data_sma]
        data += [self.divergence]
        data += [self.divergence_only]

        # Grid and ticks
        length = len(data[0])
        axs[0].grid(which='major', axis='both')
        axs[0].set_xticks(range(0, length+1, length//12))
        axs[1].grid(which='major', axis='both')
        axs[1].set_xticks(range(0, length+1, length//12))
        axs[1].set_ylim([-5, 105])
        axs[2].grid(which='major', axis='both')
        axs[2].tick_params(axis='x', labelrotation=45)

        # Plot
        dates = [self.history.iloc[index]['date'].strftime(ui.DATE_FORMAT2) for index in range(length)]
        axs[0].plot(dates, data[0], '-', color='blue', label='Price', linewidth=0.5)
        axs[0].plot(dates, data[1], '-', color='orange', label=f'SMA{self.price.interval}', linewidth=1.5)
        axs[1].plot(dates, data[2], '-', color='blue', label=self.type.upper(), linewidth=0.5)
        axs[1].plot(dates, data[3], '-', color='orange', label=f'SMA{self.price.interval}', linewidth=1.5)
        axs[2].plot(dates[self.price.periods:], data[4][self.price.periods:], '-', color='orange', label='Divergence', linewidth=1.0)
        axs[2].plot(dates[self.price.periods:], data[5][self.price.periods:], '-', color='green', label='Divergence', linewidth=1.0)
        axs[2].hlines(y=0.0, xmin=dates[0], xmax=dates[-1], color='black', linewidth=1.5)

        # Legend
        axs[0].legend(loc='best')
        axs[1].legend(loc='best')

        if show:
            plt.figure(figure)
            plt.show()

        return figure


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    # logger.get_logger(logging.DEBUG)

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'IBM'
    div = Divergence(ticker)
    div.calculate()
    div.plot()
