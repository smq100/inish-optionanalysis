import time
import threading
import logging

import matplotlib.pyplot as plt

from analysis.trend import SupportResistance
from data import store as store
from utils import utils


_logger = utils.get_logger(logging.WARNING, logfile='')

class Interface:
    def __init__(self, ticker:str, days:int=1000, quick:bool=False, exit:bool=False):
        self.tickers = [ticker.upper()]
        self.days = days
        self.quick = quick
        self.exit = exit
        self.trend:SupportResistance = None
        self.task:threading.Thread = None

        if store.is_ticker(ticker.upper()):
            if self.exit:
                self.calculate_support_and_resistance()
            else:
                self.main_menu()
        else:
            utils.print_error(f'Invalid ticker: {self.tickers[0]}')
            self.tickers[0] = ''
            if not self.exit:
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

            if self.tickers is not None:
                menu_items['1'] = f'Change Ticker ({", ".join(self.tickers)})'

            if self.quick:
                menu_items['4'] += ' (quick)'

            selection = utils.menu(menu_items, 'Select Operation', 0, 4)

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
                    self.tickers[0] = ticker
                else:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def add_ticker(self):
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.tickers += [ticker]
                else:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = utils.input_integer('Enter number of days: ', 30, 9999)

    def calculate_support_and_resistance(self):
        if self.quick:
            self.trend = SupportResistance(self.tickers[0], days=self.days)
        else:
            methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
            extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
            self.trend = SupportResistance(self.tickers[0], methods=methods, extmethods=extmethods, days=self.days)

        self.task = threading.Thread(target=self.trend.calculate)
        self.task.start()

        self._show_progress()

        figure = self.trend.plot()
        plt.figure(figure)
        plt.show()

        utils.print_message(f'Resitance: {self.trend.stats.res_level:.2f} (std={self.trend.stats.res_weighted_std:.2f})')
        utils.print_message(f'Support:   {self.trend.stats.sup_level:.2f} (std={self.trend.stats.sup_weighted_std:.2f})', creturn=0)

    def _show_progress(self) -> None:
        while not self.trend.task_error: pass

        if self.trend.task_error == 'None':
            utils.progress_bar(0, 0, prefix='', suffix='', length=50, reset=True)
            while self.trend.task_error == 'None':
                time.sleep(0.15)
                utils.progress_bar(0, 0, prefix='', suffix=self.trend.task_message, length=50)

            if self.trend.task_error == 'Done':
                utils.print_message(f'{self.trend.task_error}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds')
            else:
                utils.print_error(f'{self.trend.task_error}: Error extracting lines')

        else:
            utils.print_message(f'{self.trend.task_error}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Technical Analysis')
    parser.add_argument('-t', '--ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', help='Days to run analysis', default=1000)
    parser.add_argument('-q', '--quick', help='Run quick analysis', action='store_true')
    parser.add_argument('-x', '--exit', help='Run trend analysis then exit (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(ticker=command['ticker'], days=int(command['days']), quick=command['quick'], exit=command['exit'])
    else:
        Interface('AAPL', days=int(command['days']), quick=command['quick'])
