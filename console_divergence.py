import time
import threading
import logging

import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

from analysis.divergence import Divergence
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, list: str = '', days: int = 100, disp_calc: bool = False, disp_plot: bool = False, disp_anly: bool = False, exit: bool = False):
        self.list = list.upper()
        self.days: int = days
        self.exit: bool = exit
        self.disp_calc: bool = disp_calc
        self.disp_plot: bool = disp_plot
        self.disp_anly: bool = disp_anly
        self.tickers: list[str] = []
        self.results: list[pd.DataFrame] = []
        self.analysis: pd.DataFrame = pd.DataFrame()
        self.divergence: Divergence
        self.task: threading.Thread
        self.use_cache: bool = False

        if list:
            self.select_tickers(list)

        if exit and self.tickers:
            self.calculate_divergence()
        elif self.tickers:
            self.calculate_divergence()
            self.main_menu()
        else:
            self.main_menu()

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': 'Select Tickers',
                '2': f'Days ({self.days})',
                '3': 'Calculate',
                '4': 'Show Analysis',
                '5': 'Show Results',
                '6': 'Show Plot',
                '0': 'Exit'
            }

            if self.tickers:
                menu_items['1'] += f' ({self.list})'

            if not self.analysis.empty:
                menu_items['4'] += f' ({len(self.analysis)})'

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1, prompt='Select operation, or 0 when done')

            if selection == 1:
                self.select_tickers()
            elif selection == 2:
                self.select_days()
            elif selection == 3:
                self.calculate_divergence()
            elif selection == 4:
                self.show_analysis()
            elif selection == 5:
                self.show_results()
            elif selection == 6:
                self.show_plot()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

    def select_tickers(self, list='') -> None:
        if not list:
            list = ui.input_text('Enter exchange, index, ticker, or \'every\'')

        self.list = list.upper()

        if self.list == 'EVERY':
            self.tickers = store.get_tickers('every')
            self.list = list.lower()
        elif store.is_exchange(list):
            self.tickers = store.get_exchange_tickers(self.list)
            self.use_cache = True
        elif store.is_index(list):
            self.tickers = store.get_index_tickers(self.list)
            self.use_cache = True
        elif store.is_ticker(list):
            self.tickers = [self.list]
        else:
            self.tickers = []
            self.list = ''
            ui.print_error(f'List \'{list}\' is not valid')

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

    def calculate_divergence(self) -> None:
        self.results = []

        if self.tickers:
            self.divergence = Divergence(self.tickers, name=self.list, days=self.days)
            if len(self.tickers) > 1:
                self.task = threading.Thread(target=self.divergence.calculate, kwargs={'cache': self.use_cache})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress()

                if self.divergence.task_state == 'Done':
                    if self.divergence.cache_used:
                        ui.print_message(f'{len(self.divergence.results)} symbols identified. Cached results used')
                    else:
                        ui.print_message(f'{len(self.divergence.results)} symbols identified in {self.divergence.task_time:.1f} seconds', pre_creturn=1)
            else:
                self.divergence.calculate(cache=self.use_cache)

                if self.disp_calc:
                    self.show_results()

                if self.disp_plot:
                    self.show_plot()

            self.calculate_analysis()

            if self.disp_anly:
                self.show_analysis()
        else:
            ui.print_error('Enter a ticker before calculating')

    def calculate_analysis(self) -> None:
        self.analysis = []
        if len(self.divergence.results) > 0:
            self.divergence.analyze()
            self.analysis = self.divergence.analysis

    def show_results(self) -> None:
        if len(self.tickers) > 0:
            if len(self.tickers) > 1:
                ticker = ui.input_text('Enter ticker')
            else:
                ticker = self.tickers[0]

            index = self._get_index(ticker)

            if index < 0:
                ui.print_error('Ticker not found in results')
            else:
                result = self.divergence.results[index]
                result = result[['date', 'price', 'rsi', 'div', 'streak']]

                name = store.get_company_name(result.index.name)
                ui.print_message(f'{name} ({result.index.name})', post_creturn=1)

                headers = ui.format_headers(result.columns, case='title')
                print(tabulate(result, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
        else:
            ui.print_error(f'No ticker(s) specified', post_creturn=1)

    def show_analysis(self) -> None:
        if len(self.analysis) > 0:
            level = ui.input_integer('Enter minimum streak length', self.divergence.streak, 100)
            df = self.analysis[self.analysis['streak'] > level]

            ui.print_message(f'Divergence Summary', post_creturn=1)
            headers = ui.format_headers(df.columns, case='title')
            print(tabulate(df, headers=headers, tablefmt=ui.TABULATE_FORMAT))
        else:
            ui.print_message(f'No divergences found', post_creturn=1)

    def show_plot(self, show: bool = True, cursor: bool = True) -> None:
        if len(self.tickers) > 0:
            if len(self.tickers) > 1:
                ticker = ui.input_text('Enter ticker')
            else:
                ticker = self.tickers[0]

            index = self._get_index(ticker)

            if index < 0:
                ui.print_error('Ticker not found in results')
            else:
                axes: list[plt.Axes]
                figure: plt.Figure
                figure, axes = plt.subplots(nrows=3, figsize=ui.CHART_SIZE, sharex=True)

                plt.style.use(ui.CHART_STYLE)
                plt.margins(x=0.1)
                plt.subplots_adjust(bottom=0.15)

                name = store.get_company_name(ticker)
                figure.canvas.manager.set_window_title(name)

                axes[0].set_title('Price')
                axes[1].set_title(self.divergence.type.upper())
                axes[2].set_title('Divergence')

                # Grid and ticks
                length = len(self.divergence.results[index])
                axes[0].grid(which='major', axis='both')
                axes[0].set_xticks(range(0, length+1, length//10))
                axes[1].grid(which='major', axis='both')
                axes[1].set_xticks(range(0, length+1, length//10))
                axes[1].set_ylim([-5, 105])
                axes[2].grid(which='major', axis='both')
                axes[2].tick_params(axis='x', labelrotation=45)

                # Plot
                dates = [self.divergence.results[index].iloc[i]['date'].strftime(ui.DATE_FORMAT2) for i in range(length)]
                axes[0].plot(dates, self.divergence.results[index]['price'], '-', color='blue', label='Price', linewidth=0.5)
                axes[0].plot(dates, self.divergence.results[index]['price_sma'], '-', color='orange', label=f'SMA{self.divergence.interval}', linewidth=1.5)
                axes[1].plot(dates, self.divergence.results[index]['rsi'], '-', color='blue', label=self.divergence.type.upper(), linewidth=0.5)
                axes[1].plot(dates, self.divergence.results[index]['rsi_sma'], '-', color='orange', label=f'SMA{self.divergence.interval}', linewidth=1.5)
                axes[2].plot(dates[self.divergence.periods:], self.divergence.results[index]['diff'][self.divergence.periods:], '-', color='orange', label='diff', linewidth=1.0)
                axes[2].plot(dates[self.divergence.periods:], self.divergence.results[index]['div'][self.divergence.periods:], '-', color='green', label='div', linewidth=1.0)
                axes[2].axhline(y=0.0, xmin=0, xmax=100, color='black', linewidth=1.5)

                # Price line limits
                min = self.divergence.results[index]['price'].min()
                max = self.divergence.results[index]['price'].max()
                axes[0].set_ylim([min*0.95, max*1.05])

                # Legend
                axes[0].legend(loc='best')
                axes[1].legend(loc='best')

                if cursor:
                    cursor = self.custom_cursor(axes, data=self.divergence.results[index])
                    figure.canvas.mpl_connect('motion_notify_event', cursor.show_xy)
                    figure.canvas.mpl_connect('axes_leave_event', cursor.hide_y)

                if show:
                    plt.figure(figure)
                    plt.show()
        else:
            ui.print_error(f'No ticker(s) specified', post_creturn=1)

    def show_progress(self) -> None:
        while not self.divergence.task_state:
            pass

        if self.divergence.task_state == 'None':
            ui.progress_bar(0, 0, suffix=self.divergence.task_message, reset=True)

            while self.divergence.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                total = self.divergence.task_total
                completed = self.divergence.task_completed
                ticker = self.divergence.task_ticker
                ui.progress_bar(completed, total, ticker=ticker, success=-1)
        elif self.divergence.task_state == 'Done':
            pass # Nothing processed. Cached results used
        else:
            ui.print_message(f'{self.divergence.task_state}')

    def _get_index(self, ticker:str):
        index = -1
        for i, item in enumerate(self.divergence.results):
            if ticker.upper() == item.index.name:
                index = i

        return index

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



def main():
    parser = argparse.ArgumentParser(description='Divergence Analysis')
    parser.add_argument('-t', '--tickers', metavar='tickers', help='Specify a ticker or list')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=100)
    parser.add_argument('-x', '--exit', help='Run divergence analysis then exit (valid only with -t)', action='store_true')
    parser.add_argument('-s', '--show_calc', help='Show calculation results', action='store_true')
    parser.add_argument('-S', '--show_plot', help='Show results plot', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(list=command['tickers'], days=int(command['days']), disp_calc=command['show_calc'], disp_plot=command['show_plot'], exit=command['exit'])
    else:
        Interface()


if __name__ == '__main__':
    main()
