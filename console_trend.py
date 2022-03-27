import time
import threading
import logging

import argparse
import matplotlib.pyplot as plt

from analysis.trend import SupportResistance
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, tickers: list[str] = [], days: int = 1000, quick: bool = False, exit: bool = False):
        self.tickers = [t.upper() for t in tickers]
        self.days = days
        self.quick = quick
        self.exit = exit
        self.trend: SupportResistance = None
        self.task: threading.Thread = None

        quit = False
        for ticker in tickers:
            if not store.is_ticker(ticker.upper()):
                ui.print_error(f'Invalid ticker: {ticker}')
                quit = True
                break

        if quit:
            pass
        elif self.exit:
            self.calculate_support_and_resistance()
        else:
            self.main_menu()

    def main_menu(self):
        while True:
            menu_items = {
                '1': 'Change Ticker',
                '2': 'Add Ticker',
                '3': f'Days ({self.days})',
                '4': 'Calculate Support & Resistance',
                '0': 'Exit'
            }

            if self.tickers:
                menu_items['1'] = f'Change Ticker ({", ".join(self.tickers)})'

            if self.quick:
                menu_items['4'] += ' (quick)'

            selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.select_ticker()
            if selection == 2:
                self.add_ticker()
            elif selection == 3:
                self.select_days()
            elif selection == 4:
                self.calculate_support_and_resistance()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

    def select_ticker(self):
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

    def add_ticker(self):
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
            self.days = ui.input_integer('Enter number of days: ', 30, 9999)

    def calculate_support_and_resistance(self):
        if self.tickers:
            ui.progress_bar(0, 0, reset=True)

            for ticker in self.tickers:
                if self.quick:
                    self.trend = SupportResistance(ticker, days=self.days)
                else:
                    methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
                    extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
                    self.trend = SupportResistance(ticker, methods=methods, extmethods=extmethods, days=self.days)

                self.task = threading.Thread(target=self.trend.calculate)
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress()

                figure = self.trend.plot()
                plt.figure(figure)

            print()
            plt.show()
        else:
            ui.print_error('Enter a ticker before calculating')

    def show_progress(self) -> None:
        while not self.trend.task_error:
            pass

        if self.trend.task_error == 'None':
            ui.progress_bar(0, 0, suffix=self.trend.task_message, reset=True)

            while self.trend.task_error == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, suffix=self.trend.task_message)

            if self.trend.task_error == 'Hold':
                pass
            elif self.trend.task_error == 'Done':
                ui.print_message(f'{self.trend.task_error}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds')
            else:
                ui.print_error(f'{self.trend.task_error}: Error extracting lines')
        else:
            ui.print_message(f'{self.trend.task_error}')


def main():
    parser = argparse.ArgumentParser(description='Technical Analysis')
    parser.add_argument('-t', '--tickers', nargs='+', help='Run using tickers')
    parser.add_argument('-d', '--days', help='Days to run analysis', default=1000)
    parser.add_argument('-q', '--quick', help='Run quick analysis', action='store_true')
    parser.add_argument('-x', '--exit', help='Run trend analysis then exit (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(tickers=command['tickers'], days=int(command['days']), quick=command['quick'], exit=command['exit'])
    else:
        Interface(days=int(command['days']), quick=command['quick'])


if __name__ == '__main__':
    main()