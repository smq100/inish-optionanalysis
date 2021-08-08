import os
import time
import threading
import logging

from screener.screener import Screener
import data as d
from data import store as store
from utils import utils as utils

logger = utils.get_logger(logging.ERROR)

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = '.screen'


class Interface:
    def __init__(self, table='', screen='', run=False, live=False):
        self.table = table.upper()
        self.screen = screen
        self.run = run
        self.live = live
        self.results = []
        self.valids = 0
        self.screener = None
        self.type = ''
        self.task = None

        if self.table:
            if self.table == 'ALL':
                self.type = 'all'
            elif store.is_exchange(self.table):
                self.type = 'exchange'
            elif store.is_index(self.table):
                self.type = 'index'
            elif store.is_ticker_valid(self.table):
                self.type = 'symbol'
            else:
                raise ValueError(f'Exchange or index not found: {table}')

            self.screener = Screener(table=self.table, live=self.live)

        if self.screen:
            if self.screener is None:
                self.screen = ''
                utils.print_error('Must specify table with screener')
            elif os.path.exists(BASEPATH+screen+SCREEN_SUFFIX):
                self.screen = BASEPATH + self.screen + SCREEN_SUFFIX
                if not self.screener.load_script(self.screen):
                    self.screen = ''
                    utils.print_error('Invalid screen script')
            else:
                utils.print_error(f'File "{self.screen}" not found')
                self.screen = ''

        if self.run:
            self.main_menu(selection=6)
        else:
            self.main_menu()

    def main_menu(self, selection=0):
        while True:
            source = 'live' if self.live else d.ACTIVE_DB
            menu_items = {
                '1': f'Select Data Source ({source})',
                '2': 'Select Exchange',
                '3': 'Select Index',
                '4': 'Select Ticker',
                '5': 'Select Screener',
                '6': 'Run Screen',
                '7': 'Show Results',
                '0': 'Exit'
            }

            if self.table:
                if self.type == 'all':
                    menu_items['2'] = f'Select Exchange (all, {len(self.screener.companies)} Symbols)'
                    menu_items['3'] = f'Select Index (all, {len(self.screener.companies)} Symbols)'
                elif self.type == 'exchange':
                    menu_items['2'] = f'Select Exchange ({self.table}, {len(self.screener.companies)} Symbols)'
                elif self.type == 'symbol':
                    menu_items['4'] = f'Select Ticker ({self.table})'
                else:
                    menu_items['3'] = f'Select Index ({self.table}, {len(self.screener.companies)} Symbols)'

            if self.screen:
                filename = os.path.basename(self.screen)
                head, sep, tail = filename.partition('.')
                menu_items['5'] = f'Select Screener ({head})'

            if len(self.results) > 0:
                menu_items['7'] = f'Show Results ({self.valids})'

            if selection == 0:
                selection = utils.menu(menu_items, 'Select Operation', 0, 7)

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
                    if self.run:
                        self.print_results()
                    elif len(self.results) < 20:
                        self.print_results()
            elif selection == 7:
                self.print_results()
            elif selection == 0:
                self.run = True

            if self.run:
                break

            selection = 0

    def select_source(self):
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

        if self.table:
            self.screener = Screener(table=self.table, script=self.screen, live=self.live)

    def select_exchange(self):
        menu_items = {}
        for exchange, item in enumerate(d.EXCHANGES):
            menu_items[f'{exchange+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Exchange', 0, len(d.EXCHANGES))
        if selection > 0:
            exc = d.EXCHANGES[selection-1]['abbreviation']
            if len(store.get_exchange_tickers(exc)) > 0:
                self.screener = Screener(exc, script=self.screen, live=self.live)
                if self.screener.valid():
                    self.table = exc
                    self.type = 'exchange'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Exchange {exc} has no symbols')

    def select_index(self):
        menu_items = {}
        for index, item in enumerate(d.INDEXES):
            menu_items[f'{index+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Index', 0, len(d.INDEXES))
        if selection > 0:
            index = d.INDEXES[selection-1]['abbreviation']
            if len(store.get_index_tickers(index)) > 0:
                self.screener = Screener(index, script=self.screen, live=self.live)
                if self.screener.valid():
                    self.table = index
                    self.type = 'index'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Index {index} has no symbols')

    def select_ticker(self):
        ticker = utils.input_text('Enter ticker: ')
        ticker = ticker.upper()
        if store.is_ticker_valid(ticker):
            self.screener = Screener(ticker, script=self.screen, live=self.live)
            if self.screener.valid():
                self.table = ticker
                self.type = 'symbol'
        else:
            self.table = ''
            self.screener = None
            utils.print_error(f'{ticker} not valid')

    def select_screen(self):
        self.script = []
        self.results = []
        self.valids = 0
        paths = []
        with os.scandir(BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    if '.screen' in entry.name:
                        self.script += [entry.path]
                        head, sep, tail = entry.name.partition('.')
                        paths += [head.title()]

        if len(self.script) > 0:
            self.script.sort()
            paths.sort()

            menu_items = {}
            for index, item in enumerate(paths):
                menu_items[f'{index+1}'] = f'{item}'
            menu_items['0'] = 'Cancel'

            selection = utils.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen = self.script[selection-1]
                self.results = []

                if self.screener is not None:
                    if not self.screener.load_script(self.screen):
                        utils.print_error('Error in script file')

        else:
            utils.print_message('No screener files found')

    def run_screen(self, progressbar=True) -> bool:
        success = False
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen:
            utils.print_error('No screen specified')
        elif self.screener.load_script(self.screen):
            self.results = []
            self.valids = 0
            self.task = threading.Thread(target=self.screener.run_script)
            self.task.start()

            if progressbar:
                self._show_progress('Progress', 'Completed')

            # Wait for thread to finish
            while self.task.is_alive(): pass

            if self.screener.task_error == 'Done':
                self.results = self.screener.results
                for result in self.results:
                    if result:
                        self.valids += 1

                utils.print_message(f'{self.valids} Symbols Identified in {self.screener.task_time:.2f} seconds')

                for i, result in enumerate(self.screener.task_results):
                    utils.print_message(f'{i+1:>2}: {result}', creturn=False)

                success = True
            else:
                self.results = []
                self.valids = 0
        else:
            utils.print_error('Script error')

        return success

    def print_results(self, all=False):
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen:
            utils.print_error('No screen specified')
        elif len(self.results) == 0:
            utils.print_message('No symbols were located')
        else:
            utils.print_message('Symbols Identified')
            index = 0

            self.results = sorted(self.results, key=str)
            for result in self.results:
                if all:
                    index += 1
                    print(f'{result} ({sum(result.values)})')
                    if (index) % 20 == 0:
                        print()
                elif result:
                    index += 1
                    print(f'{result} ', end='')
                    if (index) % 20 == 0:
                        print()

        print()

    def _show_progress(self, prefix, suffix):
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
            results = [future.result() for future in self.screener.task_futures if future.result() is not None]
            if len(results) > 0:
                [print(result) for result in results]
            else:
                print('None')
        else:
            utils.print_message(f'{self.screener.task_error}')

if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Screener')

    parser.add_argument('-t', '--table', help='Specify a symbol or table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')
    parser.add_argument('-r', '--run', help='Run the script (only valid with -t and -s)', action='store_true')

    command = vars(parser.parse_args())

    table = ''
    screen = ''

    if 'table' in command.keys():
        table = command['table']

    if 'screen' in command.keys():
        screen = command['screen']

    if screen and table and command['run']:
        Interface(table, screen, run=True)
    else:
        Interface(table, screen)
