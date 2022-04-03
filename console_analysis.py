import os
import time
import math
import threading
import logging
from datetime import datetime as dt

import argparse
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

import strategies as s
import strategies.strategy_list as sl
from strategies.strategy import Strategy
from screener.screener import Screener, Result, SCREEN_INIT_NAME, SCREEN_BASEPATH, SCREEN_SUFFIX, CACHE_BASEPATH, CACHE_SUFFIX
from analysis.trend import SupportResistance
from analysis.correlate import Correlate
from data import store as store
from utils import ui, logger

logger.get_logger(logging.WARNING, logfile='')

COOR_CUTOFF = 0.85
LISTTOP_SCREEN = 10
LISTTOP_TREND = 5
LISTTOP_CORR = 3


def _get_cache_files() -> list[str]:
    paths = []
    with os.scandir(CACHE_BASEPATH) as entries:
        for entry in entries:
            if entry.is_file():
                head, sep, tail = entry.name.partition('.')
                if tail != CACHE_SUFFIX:
                    pass
                elif head == SCREEN_INIT_NAME:
                    pass
                else:
                    paths += [head]

    if paths:
        paths.sort()

    return paths


class Interface:
    def __init__(self, table: str = '', screen: str = '', quick: bool = False, exit: bool = False):
        self.table = table.upper()
        self.screen = screen
        self.quick = quick
        self.exit = exit
        self.days = 1000
        self.auto = False
        self.path_screen = ''
        self.results_valids: list[Result] = []
        self.results_corr: list[tuple[str, pd.DataFrame.Series]] = []
        self.trend: SupportResistance = None
        self.screener: Screener = None
        self.correlate: Correlate = None
        self.strategy: Strategy = None
        self.task: threading.Thread = None
        self.ignore_cache = False

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
                ui.print_error('Exchange, index or ticker not found')

        if self.screen:
            if os.path.exists(SCREEN_BASEPATH+screen+'.'+SCREEN_SUFFIX):
                self.path_screen = f'{SCREEN_BASEPATH}{self.screen}.{SCREEN_SUFFIX}'
            else:
                ui.print_error(f'File "{self.screen}" not found')
                abort = True
                self.screen = ''

        if abort:
            pass
        elif self.table and self.path_screen:
            self.auto = True
            self.main_menu(selection=3)
        else:
            self.main_menu()

    def main_menu(self, selection: int = 0) -> None:
        while True:
            menu_items = {
                '1':  'Select Table or Ticker',
                '2':  'Select Screen',
                '3':  'Run Screen',
                '4':  'Run Option Strategy',
                '5':  'Run Support & Resistance Analysis',
                '6':  'Run Coorelation',
                '7':  'Show Top Results',
                '8':  'Show All Results',
                '9':  'Show Ticker Screen Summary',
                '10': 'Manage Cache Files',
                '11': 'Delete Old Cache Files',
                '0':  'Exit'
            }

            if self.table:
                menu_items['1'] += f' ({self.table})'

            if self.screen:
                menu_items['2'] += f' ({self.screen})'

            if self.quick:
                menu_items['5'] += ' (quick)'

            if len(self.results_valids) > 0:
                top = len(self.results_valids) if len(self.results_valids) < LISTTOP_SCREEN else LISTTOP_SCREEN
                menu_items['7'] += f' ({top})'

            if len(self.results_valids) > 0:
                menu_items['8'] += f' ({len(self.results_valids)})'

            if selection == 0:
                self.ignore_cache = True
                selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.select_list()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                self.run_screen()
                if len(self.results_valids) > 0:
                    self.show_valids(top=LISTTOP_SCREEN)
            elif selection == 4:
                self.select_option_strategy()
            elif selection == 5:
                self.select_support_resistance()
            elif selection == 6:
                self.run_coorelate()
                if len(self.results_corr) > 0:
                    self.show_coorelations()
            elif selection == 7:
                self.show_valids(top=LISTTOP_SCREEN)
            elif selection == 8:
                self.show_valids()
            elif selection == 9:
                self.show_ticker_results()
            elif selection == 10:
                self.manage_cache_files()
            elif selection == 11:
                self.clear_old_cache_files()
            elif selection == 0:
                self.exit = True

            selection = 0

            if self.exit:
                break

    def select_list(self) -> None:
        list = ui.input_alphanum('Enter exchange, index, or ticker: ').upper()
        if store.is_exchange(list):
            self.table = list
        elif store.is_index(list):
            self.table = list
        elif store.is_ticker(list):
            self.table = list
        else:
            self.table = ''
            self.screener = None
            ui.print_error(f'List {list} is not valid')

    def select_screen(self) -> None:
        self.script = []
        self.results_valids = []
        paths = []
        with os.scandir(SCREEN_BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    head, sep, tail = entry.name.partition('.')
                    if tail != SCREEN_SUFFIX:
                        pass
                    elif head == SCREEN_INIT_NAME:
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
                self.screen = paths[selection-1]
                self.path_screen = f'{SCREEN_BASEPATH}{self.screen}.{SCREEN_SUFFIX}'
        else:
            ui.print_message('No screener files found')

    def select_option_strategy(self) -> None:
        if len(self.results_valids) > 0:
            menu_items = {
                '1': 'Call',
                '2': 'Put',
                '3': 'Vertical',
                '4': 'Iron Condor',
                '5': 'Iron Butterfly',
                '0': 'Cancel',
            }

            modified = True
            selection = ui.menu(menu_items, 'Select Strategy', 0, len(menu_items))
            if selection == 1:
                strategy = 'call'
                product = 'call'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            elif selection == 2:
                strategy = 'put'
                product = 'put'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            elif selection == 3:
                strategy = 'vert'
                p = ui.input_integer('(1) Call, or (2) Put: ', 1, 2)
                product = 'call' if p == 1 else 'put'
                d = ui.input_integer('(1) Debit, or (2) Credit: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            elif selection == 4:
                strategy = 'ic'
                product = 'hybrid'
                direction = 'short'
            elif selection == 5:
                strategy = 'ib'
                product = 'hybrid'
                direction = 'short'
            else:
                modified = False

            if modified:
                self.run_option_strategy(strategy, product, direction)
        else:
            ui.print_error('No valid results to analyze')

    def select_support_resistance(self) -> list[str]:
        tickers = []
        ticker = ui.input_text("Enter ticker or 'valids': ").upper()
        if store.is_ticker(ticker):
            tickers = [ticker]
        elif ticker != 'VALIDS':
            pass
        elif len(self.results_valids) > 0:
            tickers = [str(result) for result in self.results_valids[:LISTTOP_TREND]]
        else:
            ui.print_error('Not a valid ticker')

        if tickers:
            self.run_support_resistance(tickers)

    def run_screen(self) -> bool:
        success = False
        self.auto = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.path_screen:
            ui.print_error('No screen specified')
        else:
            self.results_valids = []

            try:
                self.screener = Screener(self.table, screen=self.path_screen)
            except ValueError as e:
                ui.print_error(f'{__name__}: {str(e)}')
            else:
                self.task = threading.Thread(target=self.screener.run_script, kwargs={'ignore_cache': self.ignore_cache})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress_screen()

                if self.screener.task_state == 'Done':
                    self.results_valids = self.screener.valids
                    success = True

                    if self.screener.cache_used:
                        ui.print_message(f'{len(self.results_valids)} symbols identified. Cached results used')
                    else:
                        ui.print_message(f'{len(self.results_valids)} symbols identified in {self.screener.task_time:.1f} seconds')

        return success

    def run_option_strategy(self, strategy: str, product: str, direction: str) -> None:
        if strategy not in s.STRATEGIES:
            raise ValueError('Invalid strategy')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')

        tickers = [str(result) for result in self.results_valids[:LISTTOP_SCREEN]]

        strategies = []
        for ticker in tickers:
            if direction == 'long':
                strike = float(math.floor(store.get_last_price(ticker)))
            else:
                strike = float(math.ceil(store.get_last_price(ticker)))

            strategies += [sl.strategy_type(ticker=ticker, strategy=strategy, product=product,
                direction=direction, strike=strike, width1=0, width2=0, expiry=None, volatility=(-1.0, 0.0), load_contracts=True)]

        if len(strategies) > 0:
            sl.reset()
            self.task = threading.Thread(target=sl.analyze, args=[strategies])

            # Show thread progress. Blocking while thread is active
            tic = time.perf_counter()
            self.task.start()

            self.show_progress_options()

            toc = time.perf_counter()
            task_time = toc - tic

            if not sl.strategy_results.empty:
                ui.print_message(f'Strategy Analysis ({task_time:.1f}s)', pre_creturn=1, post_creturn=1)

                headers = [header.replace('_', ' ').title() for header in sl.strategy_results.columns]
                print(tabulate(sl.strategy_results, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
            else:
                ui.print_warning(f'No results returned: {sl.strategy_state}', pre_creturn=2, post_creturn=1)

            if len(sl.strategy_errors) > 0:
                ui.print_message('Errors', pre_creturn=1, post_creturn=1)
                for e in sl.strategy_errors:
                    print(f'{e}\n')

        else:
            ui.print_warning('No tickers to process')

    def run_support_resistance(self, tickers: list[str]) -> None:
        if tickers:
            for ticker in tickers:
                if self.quick:
                    self.trend = SupportResistance(ticker, days=self.days)
                else:
                    methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
                    extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
                    self.trend = SupportResistance(ticker, methods=methods, extmethods=extmethods, days=self.days)

                self.task = threading.Thread(target=self.trend.calculate)

                # Show thread progress. Blocking while thread is active
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress_support_resistance()

                figure = self.trend.plot()
                plt.figure(figure)

            plt.show()
        else:
            ui.print_error('No valid results to analyze')

    def run_coorelate(self) -> None:
        if len(self.results_valids) == 0:
            ui.print_error('Please run screen before correlating')
        elif not store.is_list(self.table):
            ui.print_error('List is not valid')
        else:
            table = store.get_tickers(self.table)
            self.coorelate = Correlate(table)

            self.task = threading.Thread(target=self.coorelate.compute_correlation)

            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress_correlate()

            self.results_corr = []
            for valid in self.results_valids:
                ticker = valid.company.ticker
                df = self.coorelate.get_ticker_coorelation(ticker)
                self.results_corr += [(ticker, df.iloc[-1])]

    def show_valids(self, top: int = -1, verbose: bool = False, ticker: str = '') -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        elif len(self.results_valids) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
            elif top > self.screener.task_success:
                top = self.screener.task_success

            if ticker:
                ui.print_message(f'Screener Results for {ticker} ({self.screen})')
            else:
                ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen}/{self.table})')

            index = 1
            for result in self.results_valids:
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

    def show_ticker_results(self):
        ticker = ui.input_text('Enter ticker: ').upper()
        if ticker:
            ui.print_message('Ticker Screen Results')
            for result in self.screener.results:
                [print(r) for r in result.results if ticker.ljust(6, ' ') == r[:6]]

    def show_coorelations(self):
        results = [f'{result[0]:<5}/ {result[1]["ticker"]:<5} {result[1]["value"]:.5f}' for result in self.results_corr if result[1]["value"] > COOR_CUTOFF]
        if results:
            ui.print_message('Coorelation Results')
            for result in results:
                print(result)
            if ui.input_yesno('Run support & resistance analysis on top findings?'):
                self.run_support_resistance(True)
        else:
            ui.print_message('No significant coorelations found')

    def show_progress_screen(self) -> None:
        while not self.screener.task_state:
            pass

        if self.screener.task_state == 'None':
            prefix = 'Screening'
            total = self.screener.task_total
            ui.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, reset=True)

            while self.screener.task_state == 'None':
                time.sleep(0.20)
                completed = self.screener.task_completed
                success = self.screener.task_success
                ticker = self.screener.task_ticker
                tasks = len([True for future in self.screener.task_futures if future.running()])

                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success, tasks=tasks)

    def show_progress_options(self) -> None:
        while not sl.strategy_state:
            pass

        prefix = 'Collecting Option Data'
        ui.progress_bar(0, 0, prefix=prefix, reset=True)
        if sl.strategy_state == 'None':
            while sl.strategy_state == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, prefix=prefix, suffix=sl.strategy_msg)

            if sl.strategy_state == 'Next':
                prefix = 'Analyzing Strategies'
                ui.erase_line()
                ui.progress_bar(0, 0, prefix=prefix)

                tasks = len([True for future in sl.strategy_futures if future.running()])
                while sl.strategy_state == 'Next':
                    time.sleep(0.20)
                    tasks = len([True for future in sl.strategy_futures if future.running()])
                    ui.progress_bar(sl.strategy_completed, sl.strategy_total, prefix=prefix, suffix='', tasks=tasks)

    def show_progress_support_resistance(self) -> None:
        while not self.trend.task_state:
            pass

        if self.trend.task_state == 'History':
            prefix = 'Retrieving History'
            ui.progress_bar(0, 0, prefix=prefix, reset=True)
            while self.trend.task_state == 'History':
                time.sleep(0.20)
                ui.progress_bar(0, 0, prefix=prefix, suffix=self.trend.task_message)

        if self.trend.task_state == 'None':
            prefix = 'Analyzing S & R'
            while self.trend.task_state == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, prefix=prefix, suffix=self.trend.task_message)

            if self.trend.task_state == 'Done':
                ui.print_message(f'{self.trend.task_state}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds', pre_creturn=1)
            else:
                ui.print_error(f'{self.trend.task_state}: Error extracting lines', pre_creturn=1)
        else:
            ui.print_message(f'{self.trend.task_state}')

    def show_progress_correlate(self):
        while not self.coorelate.task_state:
            pass

        if self.coorelate.task_state == 'None':
            prefix = 'Correlating'
            total = self.coorelate.task_total
            ui.progress_bar(self.coorelate.task_completed, self.coorelate.task_total, success=self.coorelate.task_success, prefix=prefix, reset=True)

            while self.task.is_alive() and self.coorelate.task_state == 'None':
                time.sleep(0.20)
                completed = self.coorelate.task_completed
                success = completed
                ticker = self.coorelate.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success)

    def manage_cache_files(self) -> None:
        paths = _get_cache_files()
        if paths:
            menu_items = {}
            for index, item in enumerate(paths):
                menu_items[f'{index+1}'] = f'{item}'
            menu_items['0'] = 'Done'

            selection = ui.menu(menu_items, 'Select cache file', 0, index+1)
            if selection > 0:
                screen = paths[selection-1]
                file = f'{CACHE_BASEPATH}{screen}.{CACHE_SUFFIX}'
                selection = ui.input_integer(f"Select operation for '{screen}': (1) Delete, (2) Rename, (0) Cancel: ", 0, 2)
                if selection == 1:
                    try:
                        os.remove(file)
                    except OSError as e:
                        ui.print_error(f'{__name__}: File error for {e.filename}: {e.strerror}')
                    else:
                        ui.print_message(f'Cache {screen} deleted')
                elif selection == 2:
                    date_time = dt.now().strftime(ui.DATE_FORMAT)
                    new_screen = f'{date_time}{screen[10:]}'
                    new_file = f'{CACHE_BASEPATH}{new_screen}.{CACHE_SUFFIX}'
                    try:
                        os.replace(file, new_file)
                    except OSError as e:
                        ui.print_error(f'File error for {e.filename}: {e.strerror}')
                    else:
                        ui.print_message(f'Renamed {screen} to {new_screen}')

        else:
            ui.print_message('No cache files found')

    def clear_old_cache_files(self):
        files = _get_cache_files()
        if files:
            old_paths = []
            date_time = dt.now().strftime(ui.DATE_FORMAT)
            for path in files:
                file_time = f'{path[:10]}'
                if file_time != date_time:
                    file = f'{CACHE_BASEPATH}{path}.{CACHE_SUFFIX}'
                    old_paths += [file]

            if old_paths:
                deleted = 0
                select = ui.input_text(f'Delete {len(old_paths)} files? (y/n): ').lower()
                if select == 'y':
                    for path in old_paths:
                        try:
                            os.remove(path)
                        except OSError as e:
                            ui.print_error(f'{__name__}: File error for {e.filename}: {e.strerror}')
                        else:
                            deleted += 1
                    ui.print_message(f'Deleted {deleted} files')
                else:
                    ui.print_message('No files deleted')
            else:
                ui.print_message('All files up to date')
        else:
            ui.print_message('No files to delete')


def main():
    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')
    parser.add_argument('-q', '--quick', help='Run a quick analysis', action='store_true')
    parser.add_argument('-v', '--verbose', help='Show verbose output', action='store_true')
    parser.add_argument('-x', '--exit', help='Run the script and quit (only valid with -t and -s) then exit', action='store_true')

    command = vars(parser.parse_args())
    table = ''
    screen = ''

    Interface(table=command['table'], screen=command['screen'], quick=command['quick'], exit=command['exit'])


if __name__ == '__main__':
    main()
