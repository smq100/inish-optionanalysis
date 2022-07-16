import matplotlib.pyplot as plt
import pandas as pd

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, logger


_logger = logger.get_logger()


class Divergence(Threaded):
    def __init__(self, ticker: str, days: int = 1000):
        self.ticker = ''
        self.history = pd.DataFrame()
        self.technical = pd.DataFrame()

        if (store.is_ticker(ticker)):
            self.ticker = ticker
        else:
            raise ValueError('{__name__}: Error initializing {__class__} with ticker {ticker}')

    def __str__(self):
        return f'Divergence analysis for {self.ticker})'

    @Threaded.threaded
    def calculate(self) -> None:
        ta = Technical(self.ticker, None, 365)
        self.history = ta.history
        self.technical = ta.calc_rsi()

    def plot(self, show: bool = True) -> plt.Figure:
        if len(self.history) == 0:
            raise ValueError('No price history')
        if len(self.technical) == 0:
            raise ValueError('No technical history')

        data: list[pd.DataFrame] = [self.history]
        data += [self.technical]

        axs: list[plt.Axes]
        figure: plt.Figure
        figure, axs = plt.subplots(nrows=len(data), figsize=ui.CHART_SIZE, sharex=True)

        plt.style.use(ui.CHART_STYLE)
        plt.margins(x=0.1)
        plt.subplots_adjust(bottom=0.15)

        figure.canvas.manager.set_window_title(self.ticker)
        axs[0].set_title('History')
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
        dates = [data[0].iloc[index]['date'].strftime(ui.DATE_FORMAT) for index in range(length)]
        axs[0].plot(dates, data[0]['close'], '-k', linewidth=0.8)
        axs[1].plot(dates, data[1], '-b', linewidth=0.8)

        if show:
            plt.figure(figure)
            plt.show()

        return figure


if __name__ == '__main__':
    import sys
    import logging
    from utils import logger

    logger.get_logger(logging.DEBUG)

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'IBM'
    div = Divergence(ticker)
    div.calculate()
    div.plot()
