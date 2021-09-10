import os
import time
import threading
import logging

from screener.screener import Screener, Result
import data as d
from data import store as store
from utils import utils as utils

logger = utils.get_logger(logging.ERROR)

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = '.screen'


class Interface:
    def __init__(self, table:str='', screen:str='', verbose:bool=False, exit:bool=False, live:bool=False):
        self.table = table.upper()
        self.screen_base = screen
        self.verbose = verbose
        self.exit = exit
        self.live = live
        self.screen_path = ''
        self.results:list[Result] = []
        self.valids = 0
        self.end = 0
        self.screener:Screener = None
        self.type = ''
        self.task:threading.Thread = None

        if self.table:
            if self.table == 'ALL':
                self.type = 'all'
            elif store.is_exchange(self.table):
                self.type = 'exchange'
            elif store.is_index(self.table):
                self.type = 'index'
            elif store.is_ticker(self.table):
                self.type = 'symbol'
            else:
                self.table = ''
                utils.print_error(f'Exchange, index or ticker not found: {self.table}')

        if self.screen_base:
            if os.path.exists(BASEPATH+screen+SCREEN_SUFFIX):
                self.screen_path = BASEPATH + self.screen_base + SCREEN_SUFFIX
            else:
                self.screen_base = ''
                utils.print_error(f'File "{self.screen_base}" not found')

        if self.table and self.screen_path:
            self.main_menu(selection=6)
        else:
            self.main_menu()

    def main_menu(self, selection:int=0) -> None:
        while True:
            source = 'live' if self.live else d.ACTIVE_DB
            menu_items = {
                '1': f'Select Data Source ({source})',
                '2': 'Select Exchange',
                '3': 'Select Index',
                '4': 'Select Ticker',
                '5': 'Select Screener',
                '6': 'Run Screen',
                '7': 'Run Backtest',
                '8': 'Show Tickers',
                '9': 'Show Results',
                '10': 'Show Ticker Results',
                '11': 'Show All',
                '0': 'Exit'
            }

            if self.table:
                if self.type == 'all':
                    menu_items['2'] = f'Select Exchange (all)'
                    menu_items['3'] = f'Select Index (all)'
                elif self.type == 'exchange':
                    menu_items['2'] = f'Select Exchange ({self.table})'
                elif self.type == 'symbol':
                    menu_items['4'] = f'Select Ticker ({self.table})'
                else:
                    menu_items['3'] = f'Select Index ({self.table})'

            if self.screen_base:
                menu_items['5'] = f'Select Screener ({self.screen_base})'

            if len(self.results) > 0:
                menu_items['8'] = f'Show Tickers ({self.valids})'
                menu_items['9'] = f'Show Results ({self.valids})'
                menu_items['11'] = f'Show All ({len(self.results)})'

            if selection == 0:
                selection = utils.menu(menu_items, 'Select Operation', 0, 11)

            if selection == 1:
                self.select_source()
            if selection == 2:
                self.select_exchange()
            if selection == 3:
                self.select_index()
            if selection == 4:
                self.select_ticker()
            elif selection == 5:
                self.select_screen()
            elif selection == 6:
                if self.run_screen():
                    if self.valids > 0:
                        self.print_results()
            elif selection == 7:
                if self.run_backtest():
                    if self.valids > 0:
                        self.print_backtest()
            elif selection == 8:
                self.print_results()
            elif selection == 9:
                self.print_results(verbose=True)
            elif selection == 10:
                self.print_ticker_results()
            elif selection == 11:
                self.print_results(all=True)
            elif selection == 0:
                self.exit = True

            selection = 0

            if self.exit:
                break


    def select_source(self) -> None:
        menu_items = {
            '1': 'Database',
            '2': 'Live',
            '0': 'Cancel',
        }

        selection = utils.menu(menu_items, 'Select Data Source', 0, 2)
        if selection == 1:
            self.live = False
        elif selection == 2:
            self.live = True

        # if self.table:
        #     self.screener = Screener(self.table, script=self.screen_path, live=self.live)

    def select_exchange(self) -> None:
        menu_items = {}
        for exchange, item in enumerate(d.EXCHANGES):
            menu_items[f'{exchange+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Exchange', 0, len(d.EXCHANGES))
        if selection > 0:
            exchange = d.EXCHANGES[selection-1]['abbreviation']
            if len(store.get_exchange_tickers(exchange)) > 0:
                self.table = exchange
                self.type = 'exchange'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Exchange {exchange} has no symbols')

    def select_index(self) -> None:
        menu_items = {}
        for i, item in enumerate(d.INDEXES):
            menu_items[f'{i+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Index', 0, len(d.INDEXES))
        if selection > 0:
            index = d.INDEXES[selection-1]['abbreviation']
            if len(store.get_index_tickers(index)) > 0:
                self.table = index
                self.type = 'index'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Index {index} has no symbols')

    def select_ticker(self) -> None:
        ticker = utils.input_text('Enter ticker: ')
        ticker = ticker.upper()
        if store.is_ticker(ticker):
            self.table = ticker
            self.type = 'symbol'
        else:
            self.table = ''
            self.screener = None
            utils.print_error(f'{ticker} not valid')

    def select_screen(self) -> None:
        self.script = []
        self.results = []
        self.valids = 0
        paths = []
        with os.scandir(BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    if SCREEN_SUFFIX in entry.name:
                        self.script += [entry.path]
                        head, sep, tail = entry.name.partition('.')
                        paths += [head]

        if len(self.script) > 0:
            self.script.sort()
            paths.sort()

            menu_items = {}
            for index, item in enumerate(paths):
                menu_items[f'{index+1}'] = f'{item.title()}'
            menu_items['0'] = 'Cancel'

            selection = utils.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen_base = paths[selection-1]
                self.screen_path = BASEPATH + self.screen_base + SCREEN_SUFFIX
                self.results = []
        else:
            utils.print_message('No screener files found')

    def run_screen(self, backtest:bool=False) -> bool:
        success = False
        if not self.table:
            utils.print_error('No exchange, index, or ticker specified')
        elif not self.screen_path:
            utils.print_error('No screen specified')
        else:
            if not backtest:
                self.end = 0

            try:
                self.screener = Screener(self.table, screen=self.screen_path, end=self.end, live=self.live)
            except ValueError as e:
                utils.print_error(str(e))
            else:
                self.results = []
                self.valids = 0
                self.task = threading.Thread(target=self.screener.run_script)
                self.task.start()

                self._show_progress('Progress', 'Completed')

                # Wait for thread to finish
                while self.task.is_alive(): pass

                if self.screener.task_error == 'Done':
                    self.results = sorted(self.screener.results, reverse=True, key=lambda r: float(r))
                    for result in self.results:
                        if result:
                            self.valids += 1

                    utils.print_message(f'{self.valids} Symbols Identified in {self.screener.task_time:.2f} seconds')

                    for i, result in enumerate(self.screener.task_results):
                        utils.print_message(f'{i+1:>2}: {result}')

                    success = True

        return success

    def run_backtest(self) -> bool:
        input = utils.input_integer('Input number of days (10-100): ', 10, 100)
        self.end = input

        success = self.run_screen(backtest=True)
        if success:
            for result in self.results:
                if result:
                    result.price_last = result.company.get_last_price()
                    result.price_current = store.get_last_price(result.company.ticker)
                    result.backtest_success = (result.price_current > result.price_last)

        return success

    def print_results(self, top:int=20, verbose:bool=False, all:bool=False, ticker:str='') -> None:
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen_base:
            utils.print_error('No screen specified')
        elif len(self.results) == 0:
            utils.print_message('No results were located')
        else:
            utils.print_message(f'Screener {top} of {self.screener.task_success} ({self.screen_base})')

            index = 1
            for result in self.results:
                if ticker:
                    [print(r) for r in result.results if ticker.upper().ljust(6, ' ') == r[:6]]
                elif all:
                    [print(r) for r in result.results]
                elif self.verbose or verbose:
                    [print(r) for r in result.results if result]
                elif result:
                    print(f'{index:>3}: {result} ({float(result):.2f})')
                    index += 1

                if index > top:
                    break
        print()

    def print_backtest(self, top:int=20):
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen_base:
            utils.print_error('No screen specified')
        elif len(self.results) == 0:
            utils.print_message('No results were located')
        else:
            utils.print_message(f'Backtester {top} of {self.screener.task_success} ({self.screen_base})')

            index = 1
            for result in self.results:
                if result:
                    mark = '*' if result.backtest_success else ' '
                    print(f'{index:>3}: {mark} {result} ({float(result):.2f}) C=${result.price_current:.2f}, L=${result.price_last:.2f}')
                    index += 1

                if index > top:
                    break

    def print_ticker_results(self):
        ticker = utils.input_text('Enter ticker: ')
        if ticker:
            ticker = ticker.upper()
            if store.is_ticker(ticker):
                self.print_results(ticker=ticker)

    def _show_progress(self, prefix, suffix) -> None:
        # Wait for thread to initialize
        while not self.screener.task_error: pass

        if self.screener.task_error == 'None':
            utils.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, suffix=suffix, length=50, reset=True)
            while self.task.is_alive and self.screener.task_error == 'None':
                time.sleep(0.20)
                total = self.screener.task_total
                completed = self.screener.task_completed
                success = self.screener.task_success
                ticker = self.screener.task_ticker
                tasks = len([True for future in self.screener.task_futures if future.running()])

                utils.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=ticker, length=50, success=success, tasks=tasks)

            utils.print_message('Processed Messages')
            # print(self.task.join())
            results = [future.result() for future in self.screener.task_futures if future.result() is not None]
            if len(results) > 0:
                [print(result) for result in results]
            else:
                print('None')
        else:
            utils.print_message(f'{self.screener.task_error}')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')
    parser.add_argument('-r', '--run', help='Run the script (only valid with -t and -s)', action='store_true')
    parser.add_argument('-v', '--verbose', help='Show verbose output', action='store_true')

    command = vars(parser.parse_args())

    table = ''
    screen = ''

    if 'table' in command.keys():
        table = command['table']

    if 'screen' in command.keys():
        screen = command['screen']

    if screen and table and command['run']:
        Interface(table, screen, verbose=command['verbose'], exit=True)
    else:
        Interface(table, screen, verbose=command['verbose'])
