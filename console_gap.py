import datetime as dt
import argparse
import logging
import threading
import time

import numpy as np
from pandas.tseries.holiday import USFederalHolidayCalendar
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from tabulate import tabulate

from analysis.chart import Chart
from analysis.gap import Gap
from data import store as store
from utils import logger, ui

logger.get_logger(logging.WARNING, logfile='')

DAYS_DEFAULT = 300
THRESHOLD_DEFAULT = 0.01

class Interface:
    def __init__(self, table: str = '', days: int = DAYS_DEFAULT, disp_plot: bool = False, exit: bool = False):
        self.table = table.upper()
        self.days: int = days
        self.threshold: float = THRESHOLD_DEFAULT
        self.type: str = 'a'
        self.disp_plot: bool = disp_plot
        self.exit: bool = exit
        self.tickers: list[str] = []
        self.commands: list[dict] = []
        self.gap: Gap | None = None
        self.task: threading.Thread
        self.use_cache: bool = True
        self.dirty: bool = True

        if table:
            self.m_select_tickers(table)

        self.main_menu()

    def main_menu(self) -> None:
        self.commands = [
            {'menu': 'Select Tickers', 'function': self.m_select_tickers, 'condition': 'self.tickers', 'value': 'self.table'},
            {'menu': 'Parameters', 'function': self.m_select_parameters, 'condition': 'True', 'value': 'f"{self.days}/{self.threshold}/{self.type}"'},
            {'menu': 'Calculate & Analyze', 'function': self.m_calculate, 'condition': '', 'value': ''},
            {'menu': 'Show Results', 'function': self.m_show_results, 'condition': 'not self.dirty', 'value': 'str(len(self.gap.results))'},
            {'menu': 'Show Analysis', 'function': self.m_show_analysis, 'condition': 'not self.dirty', 'value': 'str(len(self.gap.analysis))'},
            {'menu': 'Show Plot', 'function': self.m_show_plot, 'condition': '', 'value': ''}
        ]

        # Create the menu
        menu_items = {str(i+1): f'{self.commands[i]["menu"]}' for i in range(len(self.commands))}

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while not self.exit:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))
            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                self.exit = True

    def m_select_tickers(self, list='') -> None:
        if not list:
            list = ui.input_table(True, True, True, True)

        self.table = list.upper()
        self.tickers = store.get_tickers(list)

        if self.tickers:
            self.m_calculate()
        else:
            self.table = ''
            ui.print_error(f'List \'{list}\' is not valid')

    def m_select_parameters(self):
        self.days = ui.input_integer(f'Enter number of days ({self.days})', 30, 9999, self.days)
        self.threshold = ui.input_float(f'Enter threshold ({self.threshold})', 0.0, 0.1, self.threshold)
        value = ui.input_text("Enter type ('a', 'u', or 'd') or 'x' to cancel", valids = ['a', 'u', 'd', 'x'], default=self.type)
        if value != 'x':
            self.type = value

        if self.tickers:
            self.m_calculate()

    def m_calculate(self) -> None:
        if self.tickers:
            self.dirty = True
            self.gap = Gap(self.tickers, name=self.table, days=self.days, threshold=self.threshold)
            if len(self.tickers) > 1:
                self.task = threading.Thread(target=self.gap.calculate, kwargs={'use_cache': self.use_cache})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress()

                if self.gap.task_state == 'Done':
                    if self.gap.cache_used:
                        ui.print_message(f'{len(self.gap.results)} symbols identified. Cached results from {self.gap.cache_date} used')
                    else:
                        ui.print_message(f'{len(self.gap.results)} symbols identified in {self.gap.task_time:.1f} seconds', pre_creturn=1)
            else:
                self.gap.calculate(use_cache=self.use_cache)

            self.use_cache = True

            self.analyze()
            self.m_show_analysis()

            if len(self.tickers) == 1:
                self.m_show_results()

            if self.disp_plot:
                self.m_show_plot()
        else:
            ui.print_error('Enter a ticker before calculating')

    def analyze(self) -> None:
        if len(self.gap.results) > 0:
            self.gap.analyze(type=self.type)
            self.dirty = False

    def m_show_results(self) -> None:
        if self.gap.results:
            if len(self.tickers) > 1:
                ticker = ui.input_text('Enter ticker')
            else:
                ticker = self.tickers[0]

            index = self._get_index(ticker)
            if index < 0:
                ui.print_error('Ticker not found in results')
            else:
                ui.print_message(f'Results for {ticker}', pre_creturn=1, post_creturn=1)
                headers = ui.format_headers(self.gap.results[index].columns, case='title')
                print(tabulate(self.gap.results[index], headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
        else:
            ui.print_error(f'No results to show', post_creturn=1)

    def m_show_analysis(self) -> None:
        if self.gap:
            if len(self.gap.analysis) > 0:
                ui.print_message('Analysis', pre_creturn=1, post_creturn=1)
                headers = ui.format_headers(self.gap.analysis.columns, case='title')
                print(tabulate(self.gap.analysis[:20], headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
            else:
                ui.print_message(f'No analysis found', post_creturn=1)
        else:
            ui.print_error(f'Must first run calculation', post_creturn=1)

    def m_show_plot(self, cursor: bool = False) -> None:
        if len(self.gap.results) > 0:
            if len(self.tickers) > 1:
                ticker = ui.input_text('Enter ticker')
                index = self._get_index(ticker)
            else:
                ticker = self.tickers[0]
                index = 0

            if index < 0:
                ui.print_error('Ticker not found in results')
            else:
                chart = Chart(ticker, days=self.days)
                figure, ax = chart.plot_ohlc()
                length = len(chart.history)

                c = [result.index for result in self.gap.results[index].itertuples() if result.unfilled > 0.0]
                cmap = plt.cm.get_cmap('tab20', len(c))

                i = 0
                starts = []
                ends = []
                filled = []

                start = self.gap.results[-1].attrs['last']
                end = dt.datetime.now().date()
                calendar = USFederalHolidayCalendar()
                holidays = calendar.holidays(start, end).date.tolist()
                offset = np.busday_count(str(start), str(end), weekmask=[1,1,1,1,1,0,0], holidays=holidays)

                for result in self.gap.results[index].itertuples():
                    if result.unfilled > 0.0:
                        starts.append(result.start)
                        ends.append(result.start+result.gap)

                        if result.gap > 0.0:
                            filled.append(result.start + result.unfilled)
                        else:
                            filled.append(result.start - result.unfilled)

                        ax.axhspan(starts[-1], ends[-1], xmin=0, xmax=length, facecolor=cmap(i), alpha=0.25) # Full gap
                        ax.axhspan(ends[-1], filled[-1], xmin=0, xmax=length, facecolor=cmap(i), alpha=0.25) # Filled portion
                        ax.axvline(result.index-offset, ls='--', lw=1.5, color=cmap(i), alpha=0.5) # Index of gap
                        i += 1

                if cursor:
                    cursor = Cursor(ax, vertOn=False, color='b', linewidth=0.8)

                if not starts:
                    ui.print_message('No unfilled gaps to plot')
                else:
                    plt.figure(figure)
                    plt.show()
        else:
            ui.print_error(f'No gaps', post_creturn=1)

    def show_progress(self) -> None:
        while not self.gap.task_state:
            pass

        if self.gap.task_state == 'None':
            print()
            prefix = 'Fetching Data'
            ui.progress_bar(0, 0, prefix=prefix, suffix=self.gap.task_message, reset=True)

            while self.gap.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                total = self.gap.task_total
                completed = self.gap.task_completed
                ticker = self.gap.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=-1)

            print()
        elif self.gap.task_state == 'Done':
            pass  # Nothing processed. Cached results used
        else:
            ui.print_message(f'{self.gap.task_state}')

    def _get_index(self, ticker: str):
        index = -1
        if self.gap.results:
            for i, item in enumerate(self.gap.results):
                if ticker.upper() == item.index.name:
                    index = i
                    break

        return index


def main():
    parser = argparse.ArgumentParser(description='Gap Analysis')
    parser.add_argument('-t', '--tickers', metavar='tickers', help='Specify a ticker or list')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=DAYS_DEFAULT)
    parser.add_argument('-s', '--show_plot', help='Show results plot', action='store_true')
    parser.add_argument('-x', '--exit', help='Run quit (only valid with -t) then exit', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(table=command['tickers'], days=int(command['days']), disp_plot=command['show_plot'], exit=command['exit'])
    else:
        Interface()


if __name__ == '__main__':
    main()
