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
    def __init__(self, tickers: list[str] = [], days: int = 100, show_table: bool = False, show_plot: bool = False, exit: bool = False):
        self.tickers: str = [t.upper() for t in tickers]
        self.days: int = days
        self.exit: bool = exit
        self.show_table: bool = show_table
        self.show_plot: bool = show_plot
        self.results: list[pd.DataFrame] = []
        self.analysis: list[pd.DataFrame] = []
        self.divergence: Divergence | None = None
        self.task: threading.Thread | None = None

        quit = False
        for ticker in tickers:
            if not store.is_ticker(ticker.upper()):
                ui.print_error(f'Invalid ticker: {ticker}')
                quit = True
                break

        if quit:
            pass
        elif self.exit:
            self.calculate_divergence()
        else:
            self.main_menu()

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': 'Change Ticker',
                '2': 'Add Ticker',
                '3': f'Days ({self.days})',
                '4': 'Calculate Divergence',
                '5': 'Show Results',
                '0': 'Exit'
            }

            if self.tickers:
                menu_items['1'] = f'Change Ticker ({", ".join(self.tickers)})'

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1, prompt='Select operation, or 0 when done')

            if selection == 1:
                self.select_ticker()
            if selection == 2:
                self.add_ticker()
            elif selection == 3:
                self.select_days()
            elif selection == 4:
                self.calculate_divergence()
            elif selection == 5:
                self.show_results()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

    def select_ticker(self) -> None:
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.tickers = [ticker]
                else:
                    ui.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def add_ticker(self) -> None:
        valid = False

        while not valid:
            ticker = input('Please enter ticker, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.tickers += [ticker]
                else:
                    ui.print_error('Invalid ticker. Try again or enter 0 to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

    def calculate_divergence(self) -> None:
        self.results = []
        self.analysis = []

        if self.tickers:
            self.divergence = Divergence(self.tickers, days=self.days)
            self.results += self.divergence.calculate()
            self.analysis += self.divergence.analyze()

            # self.task = threading.Thread(target=self.divergence.calculate)
            # self.task.start()

            # # Show thread progress. Blocking while thread is active
            # self.show_progress()

            if self.show_table:
                self.show_results()

            if self.show_plot:
                figure = self.divergence.plot(0)
                plt.figure(figure)
        else:
            ui.print_error('Enter a ticker before calculating')

    def show_results(self) -> None:
        for result in self.results:
            name = store.get_company_name(result.index.name)
            headers = ui.format_headers(result.columns, case='lower')
            ui.print_message(f'{name} ({result.index.name})', post_creturn=1)
            print(tabulate(result, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.3f'))

    def show_progress(self) -> None:
        while not self.divergence.task_state:
            pass

        if self.divergence.task_state == 'None':
            ui.progress_bar(0, 0, suffix=self.divergence.task_message, reset=True)

            while self.divergence.task_state == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, suffix=self.divergence.task_message)

            if self.divergence.task_state == 'Hold':
                pass
            elif self.divergence.task_state == 'Done':
                ui.print_message(f'{self.divergence.task_state}: {self.divergence.task_total} lines calculated in {self.divergence.task_time:.1f} seconds', post_creturn=1)
            else:
                ui.print_error(f'{self.divergence.task_state}: Error calculating lines')
        else:
            ui.print_message(f'{self.divergence.task_state}')


def main():
    parser = argparse.ArgumentParser(description='Divergence Analysis')
    parser.add_argument('-t', '--ticker', metavar='ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=100)
    parser.add_argument('-x', '--exit', help='Run divergence analysis then exit (valid only with -t)', action='store_true')
    parser.add_argument('-s', '--show_table', help='Show results table', action='store_true')
    parser.add_argument('-S', '--show_plot', help='Show results plot', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(tickers=[command['ticker']], days=int(command['days']), show_table=command['show_table'], show_plot=command['show_plot'], exit=command['exit'])
    else:
        Interface()


if __name__ == '__main__':
    main()
