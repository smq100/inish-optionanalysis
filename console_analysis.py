import os
import time
import threading
import logging

import matplotlib.pyplot as plt

from screener.screener import Screener, Result, INIT_NAME
from analysis.trend import SupportResistance
from analysis.correlate import Correlate
from data import store as store
from utils import utils

_logger = utils.get_logger(logging.WARNING, logfile='')

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = 'screen'
LISTTOP = 10

class Interface:
    def __init__(self, table:str='', screen:str='', quick:bool=True, exit:bool=False):
        self.table = table.upper()
        self.screen_base = screen
        self.quick = quick
        self.exit = exit
        self.days = 1000
        self.auto = False
        self.screen_path = ''
        self.results:list[Result] = []
        self.results_corr:list[str] = []
        self.valids = 0
        self.screener:Screener = None
        self.correlate:Correlate = None
        self.task:threading.Thread = None

        abort = False

        if self.table:
            if self.table == 'ALL':
                pass
            elif store.is_exchange(self.table):
                pass
            elif store.is_index(self.table):
                pass
            elif store.is_ticker(self.table):
                pass
            else:
                self.table = ''
                abort = True
                utils.print_error('Exchange, index or ticker not found')

        if self.screen_base:
            if os.path.exists(BASEPATH+screen+'.'+SCREEN_SUFFIX):
                self.screen_path = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
            else:
                utils.print_error(f'File "{self.screen_base}" not found')
                abort = True
                self.screen_base = ''

        if abort:
            pass
        elif self.table and self.screen_path:
            self.auto = True
            self.main_menu(selection=3)
        else:
            self.main_menu()

    def main_menu(self, selection:int=0) -> None:
        while True:
            menu_items = {
                '1': 'Select Table',
                '2': 'Select Screen',
                '3': 'Screen',
                '4': 'Coorelate',
                '5': 'Analyze',
                '6': 'Show Top',
                '0': 'Exit'
            }

            if self.table:
                menu_items['1'] = f'Select Table ({self.table})'

            if self.screen_base:
                menu_items['2'] = f'Select Screen ({self.screen_base})'

            if selection == 0:
                selection = utils.menu(menu_items, 'Select Operation', 0, 6)

            if selection == 1:
                self.select_list()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                if self.run_screen():
                    if self.valids > 0:
                        self.print_results(top=LISTTOP)
            elif selection == 4:
                self.run_coorelate()
            elif selection == 5:
                self.run_analyze()
            elif selection == 6:
                self.print_results(top=LISTTOP)
            elif selection == 0:
                self.exit = True

            selection = 0

            if self.exit:
                break

    def select_list(self) -> None:
        list = utils.input_alphanum('Enter exchange, index, or ticker: ').upper()
        if store.is_exchange(list):
            self.table = list
        elif store.is_list(list):
            self.table = list
        elif store.is_ticker(list):
            self.table = list
        else:
            self.table = ''
            self.screener = None
            utils.print_error(f'List {list} is not valid')

    def select_screen(self) -> None:
        self.script = []
        self.results = []
        self.valids = 0
        paths = []
        with os.scandir(BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    head, sep, tail = entry.name.partition('.')
                    if tail != SCREEN_SUFFIX:
                        pass
                    elif head == INIT_NAME:
                        pass
                    elif head == 'test':
                        pass
                    else:
                        self.script += [entry.path]
                        paths += [head]

        if paths:
            self.script.sort()
            paths.sort()

            menu_items = {}
            for index, item in enumerate(paths):
                menu_items[f'{index+1}'] = f'{item.title()}'
            menu_items['0'] = 'Cancel'

            selection = utils.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen_base = paths[selection-1]
                self.screen_path = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
                self.results = []
        else:
            utils.print_message('No screener files found')

    def run_screen(self) -> bool:
        success = False
        self.auto = False

        if not self.table:
            utils.print_error('No exchange, index, or ticker specified')
        elif not self.screen_path:
            utils.print_error('No screen specified')
        else:
            try:
                self.screener = Screener(self.table, screen=self.screen_path)
            except ValueError as e:
                utils.print_error(str(e))
            else:
                self.results = []
                self.task = threading.Thread(target=self.screener.run_script)
                self.task.start()

                self._show_progress_screen('Screening')

                if self.screener.task_error == 'Done':
                    self.results = sorted(self.screener.results, reverse=True, key=lambda r: float(r))
                    self.valids = 0
                    for result in self.results:
                        if result:
                            self.valids += 1

                    utils.print_message(f'{self.valids} symbols identified in {self.screener.task_time:.1f} seconds')

                    success = True

        return success

    def run_coorelate(self) -> None:
        if len(self.results) > 0:
            table = store.get_tickers(self.table)
            self.coorelate = Correlate(table)

            self.task = threading.Thread(target=self.coorelate.compute_correlation)
            self.task.start()

            print()
            self._show_progress_correlate('Correlating')

            self.results_corr = []
            tickers = [str(result) for result in self.results if bool(result)][:LISTTOP]
            for ticker in tickers:
                df = self.coorelate.get_ticker_coorelation(ticker)
                self.results_corr += [df.iloc[-1]]

                utils.print_message(f'Highest correlations to {ticker}')
                [print(f'{result[1]:>5}: {result[2]:.5f}') for result in df.iloc[-1:-4:-1].itertuples()]

            answer = utils.input_text('Run analysis on top findings? (y/n): ').lower()
            if answer == 'y':
                self.run_analyze(True)
        else:
            utils.print_error('Run screen before correlating')

    def run_analyze(self, corr:bool=False) -> None:
        if len(self.results) > 0:
            if corr:
                tickers = [result["ticker"] for result in self.results_corr]
            else:
                tickers = [str(result) for result in self.results if bool(result)][:LISTTOP]

            utils.progress_bar(0, 0, prefix='Analyzing', reset=True)

            for ticker in tickers:
                if self.quick:
                    self.trend = SupportResistance(ticker, days=self.days)
                else:
                    methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
                    extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
                    self.trend = SupportResistance(ticker, methods=methods, extmethods=extmethods, days=self.days)

                self.task = threading.Thread(target=self.trend.calculate)
                self.task.start()

                self._show_progress_analyze('Analyzing')

                figure = self.trend.plot()
                plt.figure(figure)

            print()
            plt.show()
        else:
            utils.print_error('Run screen before analyzing')

    def print_results(self, top:int=-1, verbose:bool=False, ticker:str='') -> None:
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen_base:
            utils.print_error('No screen specified')
        elif len(self.results) == 0:
            utils.print_message('No results were located')
        else:
            if top <= 0:
                results = sorted(self.results, key=lambda r: str(r))
                top = self.screener.task_success
            elif top > self.screener.task_success:
                results = sorted(self.results, reverse=True, key=lambda r: float(r))
                top = self.screener.task_success
            else:
                results = sorted(self.results, reverse=True, key=lambda r: float(r))

            if ticker:
                utils.print_message(f'Screener Results for {ticker} ({self.screen_base})')
            else:
                utils.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen_base})')

            index = 1
            for result in results:
                if ticker:
                    [print(r) for r in result.results if ticker.upper().ljust(6, ' ') == r[:6]]
                elif verbose:
                    [print(r) for r in result.results if result]
                elif result:
                    print(f'{index:>3}: {result} ({float(result):.2f})')
                    index += 1

                if index > top:
                    break
        print()

    def _show_progress_screen(self, prefix) -> None:
        while not self.screener.task_error: pass

        utils.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, reset=True)
        while self.screener.task_error == 'None':
            time.sleep(0.20)
            total = self.screener.task_total
            completed = self.screener.task_completed
            success = self.screener.task_success
            ticker = self.screener.task_ticker
            tasks = len([True for future in self.screener.task_futures if future.running()])

            utils.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success, tasks=tasks)

    def _show_progress_correlate(self, prefix):
        while not self.coorelate.task_error: pass

        if self.coorelate.task_error == 'None':
            total = self.coorelate.task_total
            utils.progress_bar(self.coorelate.task_completed, self.coorelate.task_total, prefix=prefix, reset=True)

            while self.task.is_alive and self.coorelate.task_error == 'None':
                time.sleep(0.20)
                completed = self.coorelate.task_completed
                ticker = self.coorelate.task_ticker
                utils.progress_bar(completed, total, prefix=prefix, ticker=ticker)

    def _show_progress_analyze(self, prefix) -> None:
        while not self.trend.task_error: pass

        if self.trend.task_error == 'None':
            while self.trend.task_error == 'None':
                time.sleep(0.20)
                utils.progress_bar(0, 0, prefix=prefix, suffix=self.trend.task_message)

            if self.trend.task_error == 'Hold':
                pass
            elif self.trend.task_error == 'Done':
                utils.print_message(f'{self.trend.task_error}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds')
            else:
                utils.print_error(f'{self.trend.task_error}: Error extracting lines')
        else:
            utils.print_message(f'{self.trend.task_error}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')
    parser.add_argument('-x', '--exit', help='Run the script and quit (only valid with -t and -s) then exit', action='store_true')
    parser.add_argument('-v', '--verbose', help='Show verbose output', action='store_true')

    command = vars(parser.parse_args())
    table = ''
    screen = ''

    if 'table' in command.keys():
        table = command['table']

    if 'screen' in command.keys():
        screen = command['screen']

    if screen and table and command['exit']:
        Interface(table, screen, exit=True)
    else:
        Interface(table, screen)
