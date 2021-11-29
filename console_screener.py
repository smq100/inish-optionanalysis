import os
import time
import threading
import logging

import data as d
from screener.screener import Screener, Result, INIT_NAME
from data import store as store
from utils import ui

_logger = ui.get_logger(logging.WARNING, logfile='')

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = 'screen'


class Interface:
    def __init__(self, table:str='', screen:str='', backtest:int=0, verbose:bool=False, exit:bool=False, live:bool=False):
        self.table = table.upper()
        self.screen_base = screen
        self.verbose = verbose
        self.exit = exit
        self.live = live
        self.auto = False
        self.screen_path = ''
        self.results:list[Result] = []
        self.valids = 0
        self.screener:Screener = None
        self.task:threading.Thread = None

        abort = False

        if type(backtest) == int:
            self.end = backtest
        else:
            self.end = 0
            abort = False
            ui.print_error("'backtest' must be an integer. Using a value of 0")

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
                ui.print_error(f'Exchange, index or ticker not found: {self.table}')

        if self.screen_base:
            if os.path.exists(BASEPATH+screen+'.'+SCREEN_SUFFIX):
                self.screen_path = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
            else:
                ui.print_error(f'File "{self.screen_base}" not foundx')
                abort = True
                self.screen_base = ''

        if abort:
            pass
        elif self.table and self.screen_path and self.end > 0:
            self.auto = True
            self.main_menu(selection=5)
        elif self.table and self.screen_path:
            self.auto = True
            self.main_menu(selection=4)
        else:
            self.main_menu()

    def main_menu(self, selection:int=0) -> None:
        while True:
            source = 'live' if self.live else d.ACTIVE_DB
            menu_items = {
                '1': f'Select Data Source ({source})',
                '2': 'Select List',
                '3': 'Select Screener',
                '4': 'Run Screen',
                '5': 'Run Backtest',
                '6': 'Show All',
                '7': 'Show Top',
                '8': 'Show Ticker',
                '0': 'Exit'
            }

            if self.table:
                menu_items['2'] = f'Select List ({self.table})'

            if self.screen_base:
                menu_items['3'] = f'Select Screener ({self.screen_base})'

            if len(self.results) > 0:
                menu_items['6'] = f'Show All ({self.valids})'

            if selection == 0:
                selection = ui.menu(menu_items, 'Select Operation', 0, 8)

            if selection == 1:
                self.select_source()
            if selection == 2:
                self.select_list()
            elif selection == 3:
                self.select_screen()
            elif selection == 4:
                if self.run_screen():
                    if self.valids > 0:
                        self.print_results(top=20)
            elif selection == 5:
                if self.run_backtest(prompt=not self.auto):
                    if self.valids > 0:
                        self.print_backtest(top=20)
            elif selection == 6:
                self.print_results()
            elif selection == 7:
                self.print_results(top=20)
            elif selection == 8:
                self.print_ticker_results()
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

        selection = ui.menu(menu_items, 'Select Data Source', 0, 2)
        if selection == 1:
            self.live = False
        elif selection == 2:
            self.live = True

    def select_list(self) -> None:
        list = ui.input_text('Enter exchange, index, or ticker: ').upper()
        if store.is_exchange(list):
            self.table = list
        elif store.is_list(list):
            self.table = list
        elif store.is_ticker(list):
            self.table = list
        else:
            self.table = ''
            self.screener = None
            ui.print_error(f'List {list} is not valid')

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

            selection = ui.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen_base = paths[selection-1]
                self.screen_path = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
                self.results = []
        else:
            ui.print_message('No screener files found')

    def run_screen(self, backtest:bool=False) -> bool:
        success = False
        self.auto = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.screen_path:
            ui.print_error('No screen specified')
        else:
            if backtest:
                self.live = False
            else:
                self.end = 0

            try:
                self.screener = Screener(self.table, screen=self.screen_path, end=self.end, live=self.live)
            except ValueError as e:
                ui.print_error(str(e))
            else:
                self.results = []
                self.task = threading.Thread(target=self.screener.run_script)
                self.task.start()

                self.show_progress('Progress', '')

                if self.screener.task_error == 'Done':
                    self.results = sorted(self.screener.results, reverse=True, key=lambda r: float(r))
                    self.valids = 0
                    for result in self.results:
                        if result:
                            self.valids += 1

                    ui.print_message(f'{self.valids} symbols identified in {self.screener.task_time:.1f} seconds')

                    success = True

        return success

    def run_backtest(self, prompt:bool=True, bullish:bool=True) -> bool:
        if prompt:
            input = ui.input_integer('Input number of days (10-100): ', 10, 100)
            self.end = input

        success = self.run_screen(backtest=True)
        if success:
            for result in self.results:
                if result:
                    result.price_last = result.company.get_last_price()
                    result.price_current = store.get_last_price(result.company.ticker)

                    if bullish:
                        result.backtest_success = (result.price_current > result.price_last)
                    else:
                        result.backtest_success = (result.price_current < result.price_last)

        return success

    def print_results(self, top:int=-1, verbose:bool=False, ticker:str='') -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen_base:
            ui.print_error('No screen specified')
        elif len(self.results) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                results = sorted(self.screener.results, key=lambda r: str(r))
                top = self.screener.task_success
            elif top > self.screener.task_success:
                results = sorted(self.screener.results, reverse=True, key=lambda r: float(r))
                top = self.screener.task_success
            else:
                results = sorted(self.screener.results, reverse=True, key=lambda r: float(r))

            if ticker:
                ui.print_message(f'Screener Results for {ticker} ({self.screen_base})')
            else:
                ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen_base})')

            index = 1
            for result in results:
                if ticker:
                    [print(r) for r in result.results if ticker.upper().ljust(6, ' ') == r[:6]]
                elif self.verbose or verbose:
                    [print(r) for r in result.results if result]
                elif result:
                    print(f'{index:>3}: {result} ({float(result):.2f})')
                    index += 1

                if index > top:
                    break
        print()

    def print_backtest(self, top:int=-1):
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen_base:
            ui.print_error('No screen specified')
        elif len(self.results) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
            elif top > self.screener.task_success:
                top = self.screener.task_success

            ui.print_message(f'Backtest Results {top} of {self.screener.task_success} ({self.screen_base})')

            index = 1
            for result in self.results:
                if result:
                    mark = '*' if result.backtest_success else ' '
                    print(f'{index:>3}: {mark} {result} ({float(result):.2f}) ${result.price_last:.2f}/${result.price_current:.2f}')
                    index += 1

                if index > top:
                    break

    def print_ticker_results(self):
        ticker = ui.input_text('Enter ticker: ')
        if ticker:
            ticker = ticker.upper()
            if store.is_ticker(ticker):
                self.print_results(ticker=ticker)

    def show_progress(self, prefix, suffix) -> None:
        # Wait for thread to initialize
        while not self.screener.task_error: pass

        if self.screener.task_error == 'None':
            ui.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, suffix=suffix, reset=True)

            while self.task.is_alive and self.screener.task_error == 'None':
                time.sleep(0.20)
                total = self.screener.task_total
                completed = self.screener.task_completed
                success = self.screener.task_success
                ticker = self.screener.task_ticker
                tasks = len([True for future in self.screener.task_futures if future.running()])

                ui.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=ticker, success=success, tasks=tasks)

            ui.print_message('Processed Messages')

            results = [future.result() for future in self.screener.task_futures if future.result() is not None]
            if len(results) > 0:
                [print(result) for result in results]
            else:
                print('None')
        else:
            ui.print_message(f'{self.screener.task_error}')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')
    parser.add_argument('-b', '--backtest', help='Run a backtest (only valid with -t and -s)', required=False, default=0)
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
        Interface(table, screen, backtest=int(command['backtest']), verbose=command['verbose'], exit=True)
    else:
        Interface(table, screen, backtest=int(command['backtest']), verbose=command['verbose'])
