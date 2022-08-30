import os
import time
import threading
import logging

from tabulate import tabulate
import argparse

import data as d
import screener.screener as screener
from screener.screener import Screener, Result
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = 'screen'


class Interface:
    def __init__(self, table: str = '', screen: str = '', backtest: int = 0, exit: bool = False, live: bool = False):
        self.table = table.upper()
        self.screen_base = screen
        self.exit = exit
        self.live = live if store.is_database_connected() else True
        self.auto = False
        self.screen_path = ''
        self.valids: list[Result] = []
        self.screener: Screener
        self.task: threading.Thread

        abort = False

        if type(backtest) == int:
            self.backtest = backtest
        else:
            self.backtest = 0
            abort = False
            ui.print_error("'backtest' must be an integer. Using a value of 0")

        if self.table:
            if self.table == 'EVERY':
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
        elif self.table and self.screen_path and self.backtest > 0:
            self.auto = True
            self.main_menu(selection=5)
        elif self.table and self.screen_path:
            self.auto = True
            self.main_menu(selection=4)
        else:
            self.main_menu()

    def main_menu(self, selection: int = 0) -> None:
        while True:
            source = 'live' if self.live else d.ACTIVE_DB
            menu_items = {
                '1': f'Select Data Source ({source})',
                '2': 'Select List',
                '3': 'Select Screener',
                '4': 'Run Screen',
                '5': 'Run Backtest',
                '6': 'Show Ticker Screener Results',
                '7': 'Show Top',
                '8': 'Show All',
                '0': 'Exit'
            }

            if self.table:
                menu_items['2'] += f' ({self.table})'

            if self.screen_base:
                menu_items['3'] += f' ({self.screen_base})'

            if len(self.valids) > 0:
                menu_items['8'] += f' ({len(self.valids)})'

            if selection == 0:
                selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1, prompt='Select operation, or 0 when done')

            if selection == 1:
                self.select_source()
            if selection == 2:
                self.select_list()
            elif selection == 3:
                self.select_screen()
            elif selection == 4:
                if self.run_screen():
                    if len(self.valids) > 0:
                        self.show_valids(top=20)
            elif selection == 5:
                if self.run_backtest(prompt=not self.auto):
                    if len(self.valids) > 0:
                        self.show_backtest(top=20)
            elif selection == 6:
                self.print_ticker_results()
            elif selection == 7:
                self.show_valids(top=20)
            elif selection == 8:
                self.show_valids()
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

        selection = ui.menu(menu_items, 'Available Data Sources', 0, len(menu_items)-1, prompt='Select source, or 0 when done')
        if selection == 1:
            self.live = False
        elif selection == 2:
            self.live = True

    def select_list(self) -> None:
        list = ui.input_text('Enter exchange, index, or ticker').upper()
        if store.is_exchange(list):
            self.table = list
        elif store.is_list(list):
            self.table = list
        elif store.is_ticker(list):
            self.table = list
        else:
            self.table = ''
            ui.print_error(f'List {list} is not valid')

    def select_screen(self) -> None:
        self.script = []
        self.valids = []
        paths = []
        with os.scandir(BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    head, sep, tail = entry.name.partition('.')
                    if tail != SCREEN_SUFFIX:
                        pass
                    elif head == screener.SCREEN_INIT_NAME:
                        pass
                    elif head == 'test':
                        pass
                    else:
                        self.script += [entry.path]
                        paths += [head]

        if paths:
            self.script.sort()
            paths.sort()

            menu_items = {f'{index}': f'{item.title()}' for index, item in enumerate(paths, start=1)}
            menu_items['0'] = 'Cancel'

            selection = ui.menu(menu_items, 'Available Screens', 0, len(menu_items)+1, prompt='Select Screen, or 0 to cancel')
            if selection > 0:
                self.screen_base = paths[selection-1]
                self.screen_path = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
                self.valids = []
        else:
            ui.print_message('No screener files found')

    def run_screen(self) -> bool:
        success = False
        self.auto = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.screen_path:
            ui.print_error('No screen specified')
        else:
            if self.backtest > 0:
                self.live = False

            try:
                self.screener = Screener(self.table, screen=self.screen_path, backtest=self.backtest, live=self.live)
            except ValueError as e:
                ui.print_error(f'{__name__}: {str(e)}')
            else:
                cache = (self.backtest == 0)
                save = (self.backtest == 0)
                self.valids = []

                self.task = threading.Thread(target=self.screener.run, kwargs={'use_cache': cache, 'save_results': save})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress('Progress', '')

                if self.screener.task_state == 'Done':
                    self.valids = self.screener.valids

                    ui.print_message(f'{len(self.valids)} symbols identified in {self.screener.task_time:.1f} seconds')

                    success = True

        return success

    def run_backtest(self, prompt: bool = True, bullish: bool = True) -> bool:
        if prompt:
            input = ui.input_integer('Input number of days (10-100)', 10, 100)
            self.backtest = input

        success = self.run_screen()

        if success:
            for result in self.valids:
                if result:
                    result.price_last = result.company.get_last_price()
                    result.price_current = store.get_last_price(result.company.ticker)

                    if bullish:
                        result.backtest_success = (result.price_current > result.price_last)
                    else:
                        result.backtest_success = (result.price_current < result.price_last)

        return success

    def show_valids(self, top: int = -1, ticker: str = '') -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen_base:
            ui.print_error('No screen specified')
        elif len(self.valids) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                results = sorted(self.valids, key=lambda r: str(r))
                top = self.screener.task_success
            elif top > self.screener.task_success:
                results = sorted(self.valids, reverse=True, key=lambda r: float(r))
                top = self.screener.task_success
            else:
                results = sorted(self.valids, reverse=True, key=lambda r: float(r))

            if ticker:
                ui.print_message(f'Screener Results for {ticker} ({self.screen_base})')
            else:
                ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen_base})', post_creturn=1)

            if ticker:
                for result in results:
                    [print(r) for r in result.descriptions if ticker.upper().ljust(6, ' ') == r[:6]]
            elif results:
                drop = ['valid', 'price_last', 'price_current', 'backtest_success']
                summary = screener.summarize_results(results).drop(drop, axis=1)
                headers = [header.title() for header in summary.columns]
                print(tabulate(summary.head(top), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

        print()

    def show_backtest(self, top: int = -1):
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen_base:
            ui.print_error('No screen specified')
        elif len(self.valids) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
            elif top > self.screener.task_success:
                top = self.screener.task_success

            summary = screener.summarize_results(self.valids)
            order = ['ticker', 'score', 'backtest_success']
            summary = summary.reindex(columns=order)
            headers = ui.format_headers(summary.columns)

            ui.print_message(f'Backtest Results {top} of {self.screener.task_success} ({self.screen_base})')
            print(tabulate(summary.head(top), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

    def print_ticker_results(self):
        ticker = ui.input_text('Enter ticker')
        if ticker:
            ticker = ticker.upper()
            if store.is_ticker(ticker):
                self.show_valids(ticker=ticker)

    def show_progress(self, prefix, suffix) -> None:
        while not self.screener.task_state:
            pass

        if self.screener.task_state == 'None':
            ui.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, suffix=suffix, reset=True)

            while self.task.is_alive() and self.screener.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                total = self.screener.task_total
                completed = self.screener.task_completed
                success = self.screener.task_success
                ticker = self.screener.task_ticker
                tasks = len([True for future in self.screener.task_futures if future.running()])

                ui.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=ticker, success=success, tasks=tasks)

            ui.print_message('Processed Messages')

            results = [future.result() for future in self.screener.task_futures if future.result() is not None]
            if len(results) > 0:
                for result in results:
                    print(result)
            else:
                print('None')


def main():
    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', metavar='table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', metavar='screen', required=False, default='')
    parser.add_argument('-b', '--backtest', help='Run a backtest (only valid with -t and -s)', required=False, default=0)
    parser.add_argument('-x', '--exit', help='Run the script and quit (only valid with -t and -s) then exit', action='store_true')

    command = vars(parser.parse_args())
    table = ''
    screen = ''

    if 'table' in command.keys():
        table = command['table']

    if 'screen' in command.keys():
        screen = command['screen']

    if screen and table and command['exit']:
        Interface(table, screen, backtest=int(command['backtest']), exit=True)
    else:
        Interface(table, screen, backtest=int(command['backtest']))


if __name__ == '__main__':
    main()
