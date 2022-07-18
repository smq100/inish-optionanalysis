from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from sklearn.preprocessing import MinMaxScaler
from ta import trend

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, logger


_logger = logger.get_logger()


@dataclass
class _Data:
    history:pd.DataFrame = pd.DataFrame()
    history_sma:pd.Series = pd.Series(dtype=float)
    history_sma_diff:pd.Series = pd.Series(dtype=float)
    history_sma_colors: list[float] = field(default_factory=list)

    technical:pd.DataFrame = pd.DataFrame()
    technical_sma:pd.Series = pd.Series(dtype=float)

class Divergence(Threaded):
    def __init__(self, ticker: str, window: int = 15, days: int = 365):
        self.ticker = ''
        self.window = window
        self.days = days
        self.data = _Data()

        if (store.is_ticker(ticker)):
            self.ticker = ticker
        else:
            raise ValueError('{__name__}: Error initializing {__class__} with ticker {ticker}')

    def __str__(self):
        return f'Divergence analysis for {self.ticker})'

    @Threaded.threaded
    def calculate(self) -> None:
        ta_history = Technical(self.ticker, None, self.days)

        self.data.history = ta_history.history
        self.data.history_sma = ta_history.calc_ema(self.window)
        self.data.history_sma_diff = self.data.history_sma.diff().fillna(0.0)
        np_colors = self.data.history_sma.diff().fillna(0.0).to_numpy()
        colors = MinMaxScaler().fit_transform(np.array(np_colors.reshape(-1, 1)))
        self.data.history_sma_colors = [color[0] for color in colors]

        self.data.technical = ta_history.calc_rsi()
        self.data.technical_sma = trend.sma_indicator(self.data.technical, window=self.window, fillna=True)

    def plot(self, show: bool = True) -> plt.Figure:
        if len(self.data.history) == 0:
            raise ValueError('No price history')
        if len(self.data.technical) == 0:
            raise ValueError('No technical history')

        data: list[pd.DataFrame] = [self.data.history['close']]
        data += [self.data.technical]
        data += [self.data.history_sma]
        data += [self.data.technical_sma]


        axs: list[plt.Axes]
        figure: plt.Figure
        figure, axs = plt.subplots(nrows=2, figsize=ui.CHART_SIZE, sharex=True)

        plt.style.use(ui.CHART_STYLE)
        plt.margins(x=0.1)
        plt.subplots_adjust(bottom=0.15)

        figure.canvas.manager.set_window_title(self.ticker)
        axs[0].set_title('Price')
        axs[1].set_title('RSI')

        axs[0].grid(which='major', axis='both')
        axs[1].grid(which='major', axis='both')

        # Grid and ticks
        length = len(data[0])
        axs[0].set_xticks(range(0, length+1, int(length/12)))
        axs[0].tick_params(axis='x', labelrotation=45)
        axs[1].set_xticks(range(0, length+1, int(length/12)))
        axs[1].tick_params(axis='x', labelrotation=45)
        axs[1].set_ylim([-5, 105])

        # Data
        dates = [self.data.history.iloc[index]['date'].strftime(ui.DATE_FORMAT2) for index in range(length)]

        points = np.array([dates, data[2]]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        norm = plt.Normalize(data[2].min(), data[2].max())
        lc = LineCollection(segments, cmap='viridis', norm=norm)
        lc.set_array(self.data.history_sma_colors)
        line = axs[0].add_collection(lc)

        axs[0].plot(dates, data[0], '-', c='blue', label='Price', linewidth=0.5)
        # axs[0].plot(dates, data[2], '-', label='SMA', linewidth=1.5)

        axs[1].plot(dates, data[1], '-', c='blue', label='RSI', linewidth=0.5)
        axs[1].plot(dates, data[3], '-', c='orange', label='SMA', linewidth=1.5)

        # Legend
        axs[0].legend(loc='lower left')
        axs[1].legend(loc='lower left')

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
