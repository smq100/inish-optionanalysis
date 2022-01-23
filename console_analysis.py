import os
import time
import threading
import logging

import matplotlib.pyplot as plt
from pandas import DataFrame

import strategies as s
from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from screener.screener import Screener, Result, INIT_NAME
from analysis.trend import SupportResistance
from analysis.correlate import Correlate
from data import store as store
from utils import ui, logger

logger.get_logger(logging.WARNING, logfile='')

BASEPATH = os.getcwd() + '/screener/screens/'
SCREEN_SUFFIX = 'screen'
COOR_CUTOFF = 0.85
LISTTOP = 10
LISTTOP_TREND = 5
LISTTOP_CORR = 3


class Interface:
    def __init__(self, table: str = '', screen: str = '', quick: bool = False, exit: bool = False):
        self.table = table.upper()
        self.screen_base = screen
        self.quick = quick
        self.exit = exit
        self.days = 1000
        self.auto = False
        self.path_screen = ''
        self.results_screen: list[Result] = []
        self.valids_screen: list[Result] = []
        self.results_corr: list[tuple[str, DataFrame.Series]] = []
        self.trend: SupportResistance = None
        self.screener: Screener = None
        self.correlate: Correlate = None
        self.strategy: Strategy = None
        self.task: threading.Thread = None

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

        if self.screen_base:
            if os.path.exists(BASEPATH+screen+'.'+SCREEN_SUFFIX):
                self.path_screen = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
            else:
                ui.print_error(f'File "{self.screen_base}" not found')
                abort = True
                self.screen_base = ''

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
                '1': 'Select Table or Ticker',
                '2': 'Select Screen',
                '3': 'Run Screen',
                '4': 'Show Top Screen Results',
                '5': 'Show All Screen Results',
                '6': 'Show Ticker Screen Summary',
                '7': 'Run Coorelation',
                '8': 'Run Support & Resistance Analysis',
                '9': 'Run Option Strategy',
                '0': 'Exit'
            }

            if self.table:
                menu_items['1'] += f' ({self.table})'

            if self.screen_base:
                menu_items['2'] += f' ({self.screen_base})'

            if len(self.results_screen) > 0:
                menu_items['5'] += f' ({len(self.valids_screen)})'
                menu_items['6'] += f' ({len(self.results_screen)})'

            if self.quick:
                menu_items['8'] += ' (quick)'

            if selection == 0:
                selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.select_list()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                if self.run_screen():
                    if len(self.valids_screen) > 0:
                        self.show_valids(top=LISTTOP)
            elif selection == 4:
                self.show_valids(top=LISTTOP)
            elif selection == 5:
                self.show_valids()
            elif selection == 6:
                self.show_ticker_results()
            elif selection == 7:
                if self.run_coorelate():
                    self.show_coorelations()
            elif selection == 8:
                self.run_support_resistance()
            elif selection == 9:
                self.select_strategy()
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
        self.results_screen = []
        self.valids_screen = []
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
                self.path_screen = BASEPATH + self.screen_base + '.' + SCREEN_SUFFIX
                self.results_screen = []
        else:
            ui.print_message('No screener files found')

    def select_strategy(self) -> None:
        if len(self.valids_screen) > 0:
            menu_items = {
                '1': 'Call',
                '2': 'Put',
                '3': 'Vertical',
                '0': 'Cancel',
            }

            modified = True
            selection = ui.menu(menu_items, 'Select Strategy', 0, 3)

            if selection == 1:
                strategy = 'call'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            elif selection == 2:
                strategy = 'put'
                d = ui.input_integer('(1) Long, or (2) Short: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            elif selection == 3:
                p = ui.input_integer('(1) Call, or (2) Put: ', 1, 2)
                strategy = 'vertc' if p == 1 else 'vertp'
                d = ui.input_integer('(1) Debit, or (2) Credit: ', 1, 2)
                direction = 'long' if d == 1 else 'short'
            else:
                modified = False

            if modified:
                self.run_options(strategy, direction)
        else:
            ui.print_error('No valid results to analyze')

    def run_screen(self) -> bool:
        success = False
        self.auto = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.path_screen:
            ui.print_error('No screen specified')
        else:
            try:
                self.screener = Screener(self.table, screen=self.path_screen)
            except ValueError as e:
                ui.print_error(str(e))
            else:
                self.results_screen = []
                self.task = threading.Thread(target=self.screener.run_script)
                self.task.start()

                self.show_progress_screen()

                if self.screener.task_error == 'Done':
                    self.results_screen = sorted(self.screener.results, reverse=True, key=lambda r: float(r))
                    self.valids_screen = []
                    for result in self.results_screen:
                        if result:
                            self.valids_screen += [result]

                    ui.print_message(f'{len(self.valids_screen)} symbols identified in {self.screener.task_time:.1f} seconds')

                    success = True

        return success

    def run_coorelate(self) -> bool:
        success = False
        if len(self.results_screen) == 0:
            ui.print_error('Please run screen before correlating')
        elif not store.is_list(self.table):
            ui.print_error('List is not valid')
        else:
            table = store.get_tickers(self.table)
            self.coorelate = Correlate(table)

            self.task = threading.Thread(target=self.coorelate.compute_correlation)
            self.task.start()

            print()
            self.show_progress_correlate()

            self.results_corr = []
            tickers = [str(result) for result in self.results_screen if bool(result)][:LISTTOP]
            for ticker in tickers:
                df = self.coorelate.get_ticker_coorelation(ticker)
                self.results_corr += [(ticker, df.iloc[-1])]

            success = True

        return success

    def run_support_resistance(self, corr: bool = False) -> None:
        if len(self.valids_screen) > 0:
            if corr:
                tickers = [result[1]['ticker'] for result in self.results_corr if result[1]['value'] > COOR_CUTOFF][:LISTTOP_CORR]
            else:
                tickers = [str(result) for result in self.valids_screen[:LISTTOP_TREND]]

            ui.progress_bar(0, 0, prefix='Analyzing', reset=True)

            for ticker in tickers:
                if self.quick:
                    self.trend = SupportResistance(ticker, days=self.days)
                else:
                    methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
                    extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
                    self.trend = SupportResistance(ticker, methods=methods, extmethods=extmethods, days=self.days)

                self.task = threading.Thread(target=self.trend.calculate)
                self.task.start()

                self.show_progress_analyze()

                figure = self.trend.plot()
                plt.figure(figure)

            if tickers:
                print()
                plt.show()
        else:
            ui.print_error('No valid results to analyze')

    def run_options(self, strategy: str, direction: str) -> None:
        if strategy not in s.STRATEGIES:
            raise ValueError('Invalid strategy')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')

        tickers = [str(result) for result in self.valids_screen[:LISTTOP_TREND]]
        results = []

        print()
        ui.progress_bar(0, 0, prefix='Analyzing Options', reset=True)

        for ticker in tickers:
            name = ''
            if strategy == 'call':
                self.strategy = Call(ticker, 'call', direction, 1, 1, True)
                name = 'Call'
            elif strategy == 'put':
                self.strategy = Put(ticker, 'call', direction, 1, 1, True)
                name = 'Put'
            elif strategy == 'vertc':
                self.strategy = Vertical(ticker, 'call', direction, 1, 1, True)
                name = 'Vertical Call'
            elif strategy == 'vertp':
                self.strategy = Vertical(ticker, 'put', direction, 1, 1, True)
                name = 'Vertical Put'

            self.task = threading.Thread(target=self.strategy.analyze)
            self.task.start()

            self.show_progress_options()

            # Build output
            results += ['\n']
            results += [ui.delimeter(f'{direction.title()} {name} Options for {ticker}')]
            results += ['\n']
            results += [str(leg) for leg in self.strategy.legs]
            results += ['\n']
            results += [str(self.strategy.analysis)]

        if results:
            for result in results:
                print(result)

    def show_valids(self, top: int = -1, verbose: bool = False, ticker: str = '') -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen_base:
            ui.print_error('No screen specified')
        elif len(self.results_screen) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
                results = sorted(self.results_screen, key=lambda r: str(r))
            elif top > self.screener.task_success:
                top = self.screener.task_success
                results = sorted(self.results_screen, reverse=True, key=lambda r: float(r))
            else:
                results = sorted(self.results_screen, reverse=True, key=lambda r: float(r))

            if ticker:
                ui.print_message(f'Screener Results for {ticker} ({self.screen_base})')
            else:
                ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen_base})')

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

    def show_ticker_results(self):
        ticker = ui.input_text('Enter ticker: ').upper()
        if ticker:
            for result in self.results_screen:
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
        while not self.screener.task_error:
            pass

        prefix = 'Screening'
        total = self.screener.task_total
        ui.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, reset=True)

        while self.screener.task_error == 'None':
            time.sleep(0.20)
            completed = self.screener.task_completed
            success = self.screener.task_success
            ticker = self.screener.task_ticker
            tasks = len([True for future in self.screener.task_futures if future.running()])

            ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success, tasks=tasks)

    def show_progress_correlate(self):
        while not self.coorelate.task_error:
            pass

        if self.coorelate.task_error == 'None':
            prefix = 'Correlating'
            total = self.coorelate.task_total
            ui.progress_bar(self.coorelate.task_completed, self.coorelate.task_total, success=self.coorelate.task_success, prefix=prefix, reset=True)

            while self.task.is_alive and self.coorelate.task_error == 'None':
                time.sleep(0.20)
                completed = self.coorelate.task_completed
                success = completed
                ticker = self.coorelate.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success)

    def show_progress_analyze(self) -> None:
        while not self.trend.task_error:
            pass

        if self.trend.task_error == 'None':
            while self.trend.task_error == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, prefix='Analyzing', suffix=self.trend.task_message)

            if self.trend.task_error == 'Hold':
                pass
            elif self.trend.task_error == 'Done':
                ui.print_message(f'{self.trend.task_error}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds')
            else:
                ui.print_error(f'{self.trend.task_error}: Error extracting lines')
        else:
            ui.print_message(f'{self.trend.task_error}')

    def show_progress_options(self) -> None:
        while not self.strategy.task_error:
            pass

        if self.strategy.task_error == 'None':
            while self.strategy.task_error == 'None':
                time.sleep(0.20)
                ui.progress_bar(0, 0, prefix='Analyzing Options', suffix=self.strategy.task_message)
        else:
            ui.print_message(f'{self.strategy.task_error}')


if __name__ == '__main__':
    import argparse

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
