import time
import threading
import logging

import argparse
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

from analysis.divergence import Divergence
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, list: str = '', days: int = 100, show_table: bool = False, show_plot: bool = False, exit: bool = False):
        self.list = list.upper()
        self.days: int = days
        self.exit: bool = exit
        self.show_table: bool = show_table
        self.show_plot: bool = show_plot
        self.tickers: list[str] = []
        self.results: list[pd.DataFrame] = []
        self.analysis: list[pd.DataFrame] = []
        self.divergence: Divergence | None = None
        self.task: threading.Thread | None = None

        if list:
            self.select_tickers(list)

        if exit and self.tickers:
            self.calculate_divergence()
        else:
            self.main_menu()

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': 'Select Tickers',
                '2': f'Days ({self.days})',
                '3': 'Calculate Divergence',
                '4': 'Show Results',
                '0': 'Exit'
            }

            if self.tickers:
                menu_items['1'] += f' ({self.list})'

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1, prompt='Select operation, or 0 when done')

            if selection == 1:
                self.select_tickers()
            elif selection == 2:
                self.select_days()
            elif selection == 3:
                self.calculate_divergence()
            elif selection == 4:
                self.show_results()
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
        elif store.is_index(list):
            self.tickers = store.get_index_tickers(self.list)
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
        self.analysis = []

        if self.tickers:
            self.divergence = Divergence(self.tickers, days=self.days)
            self.task = threading.Thread(target=self.divergence.calculate)
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.divergence.task_state == 'Done':
                ui.print_message(f'{len(self.divergence.results)} symbols identified in {self.divergence.task_time:.1f} seconds', pre_creturn=1)

            if self.show_table:
                self.show_results('Progress', '')

            if self.show_plot:
                figure = self.divergence.plot(0)
                plt.figure(figure)
        else:
            ui.print_error('Enter a ticker before calculating')

    def show_results(self) -> None:
        for result in self.divergence.results:
            result = result[['date', 'price', 'rsi', 'div', 'streak']]
            name = store.get_company_name(result.index.name)
            ui.print_message(f'{name} ({result.index.name})', post_creturn=1)
            headers = ui.format_headers(result.columns, case='lower')
            print(tabulate(result, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.3f'))

    def show_progress(self) -> None:
        while not self.divergence.task_state:
            pass

        if self.divergence.task_state == 'None':
            ui.progress_bar(0, 0, suffix=self.divergence.task_message, reset=True)

            while self.divergence.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                total = self.divergence.task_total
                completed = self.divergence.task_completed
                success = self.divergence.task_success
                ticker = self.divergence.task_ticker
                ui.progress_bar(completed, total, ticker=ticker, success=success)
        else:
            ui.print_message(f'{self.divergence.task_state}')


def main():
    parser = argparse.ArgumentParser(description='Divergence Analysis')
    parser.add_argument('-t', '--tickers', metavar='tickers', help='Specify a ticker or list')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=100)
    parser.add_argument('-x', '--exit', help='Run divergence analysis then exit (valid only with -t)', action='store_true')
    parser.add_argument('-s', '--show_table', help='Show results table', action='store_true')
    parser.add_argument('-S', '--show_plot', help='Show results plot', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(list=command['tickers'], days=int(command['days']), show_table=command['show_table'], show_plot=command['show_plot'], exit=command['exit'])
    else:
        Interface()


if __name__ == '__main__':
    main()
