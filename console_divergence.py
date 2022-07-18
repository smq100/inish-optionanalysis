import time
import threading
import logging

import argparse
import matplotlib.pyplot as plt

from analysis.divergence import Divergence
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, tickers: list[str] = [], days: int = 1000, exit: bool = False):
        self.tickers = [t.upper() for t in tickers]
        self.days = days
        self.exit = exit
        self.trend: Divergence | None = None
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
        if self.tickers:
            for ticker in self.tickers:
                self.trend = Divergence(ticker, days=self.days)
                self.trend.calculate()

                # self.task = threading.Thread(target=self.trend.calculate)
                # self.task.start()

                # # Show thread progress. Blocking while thread is active
                # self.show_progress()

                figure = self.trend.plot(show=False)
                plt.figure(figure)

            plt.show()
        else:
            ui.print_error('Enter a ticker before calculating')

    def show_progress(self) -> None:
        while not self.trend.task_state:
            pass

        if self.trend.task_state == 'None':
            ui.progress_bar(0, 0, suffix=self.trend.task_message, reset=True)

            while self.trend.task_state == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, suffix=self.trend.task_message)

            if self.trend.task_state == 'Hold':
                pass
            elif self.trend.task_state == 'Done':
                ui.print_message(f'{self.trend.task_state}: {self.trend.task_total} lines calculated in {self.trend.task_time:.1f} seconds', post_creturn=1)
            else:
                ui.print_error(f'{self.trend.task_state}: Error calculating lines')
        else:
            ui.print_message(f'{self.trend.task_state}')


def main():
    parser = argparse.ArgumentParser(description='Divergence Analysis')
    parser.add_argument('-t', '--ticker', metavar='ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=200)
    parser.add_argument('-x', '--exit', help='Run divergence analysis then exit (valid only with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(tickers=command['ticker'], days=int(command['days']), exit=command['exit'])
    else:
        Interface(days=int(command['days']))


if __name__ == '__main__':
    main()
