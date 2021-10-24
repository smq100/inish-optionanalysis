import time
import threading
import logging

from analysis.trend import SupportResistance
from data import store as store
from utils import utils


_logger = utils.get_logger(logging.WARNING, logfile='')

class Interface:
    def __init__(self, ticker:str, days:int=1000, quick:bool=False, exit:bool=False):
        self.ticker = ticker.upper()
        self.days = days
        self.quick = quick
        self.exit = exit
        self.trend:SupportResistance = None
        self.tickers:list[str] = []
        self.task:threading.Thread = None

        if store.is_ticker(ticker.upper()):
            if self.exit:
                self.calculate_trends()
            else:
                self.main_menu()
        else:
            utils.print_error(f'Invalid ticker: {self.ticker}')
            self.ticker = ''
            if not self.exit:
                self.main_menu()

    def main_menu(self):
        while True:
            menu_items = {
                '1': 'Change Ticker',
                '2': f'Days ({self.days})',
                '3': 'Calculate Support & Resistance',
                '0': 'Exit'
            }

            if self.ticker is not None:
                menu_items['1'] = f'Change Ticker ({self.ticker})'

            selection = utils.menu(menu_items, 'Select Operation', 0, 3)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.select_days()
            elif selection == 3:
                self.calculate_trends()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

    def select_ticker(self):
        valid = False

        while not valid:
            self.ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if self.ticker != '0':
                valid = store.is_ticker(self.ticker)
                if not valid:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = utils.input_integer('Enter number of days: ', 30, 9999)

    def calculate_trends(self):
        if self.quick:
            self.trend = SupportResistance(self.ticker, days=self.days)
        else:
            methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
            extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
            self.trend = SupportResistance(self.ticker, methods=methods, extmethods=extmethods, days=self.days)

        self.task = threading.Thread(target=self.trend.calculate)
        self.task.start()

        self._show_progress()

        utils.print_message(f'Resitance Average: {self.trend.stats.res_modified_mean:.2f} (std={self.trend.stats.res_weighted_std:.2f})')
        utils.print_message(f'Support Average:   {self.trend.stats.sup_modified_mean:.2f} (std={self.trend.stats.sup_weighted_std:.2f})', creturn=0)
        self.trend.plot()

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
