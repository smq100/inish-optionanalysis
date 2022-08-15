from audioop import mul
import os
import time
import math
import threading
import logging
import datetime as dt
import webbrowser

import argparse
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

import strategies as s
import strategies.strategy_list as sl
import data as d
import screener.screener as screener
from screener.screener import Screener, Result
from strategies.strategy import Strategy
from analysis.support_resistance import SupportResistance
from analysis.correlate import Correlate
from analysis.chart import Chart
from data import store as store
import etrade.auth as auth
from utils import ui, cache, logger
from utils import math as m

logger.get_logger(logging.WARNING, logfile='')

COOR_CUTOFF = 0.85
LISTTOP_SCREEN = 10
LISTTOP_ANALYSIS = 25
LISTTOP_TREND = 5
LISTTOP_CORR = 10


def _auth_callback(url: str) -> str:
    webbrowser.open(url)
    code = ui.input_alphanum('Please accept agreement and enter text code from browser')
    return code


class Interface:
    table: str
    screen: str
    quick: bool
    exit: bool
    days: int
    results_corr: list[tuple[str, pd.Series]]
    screener: Screener | None
    trend: SupportResistance
    correlate: Correlate
    chart: Chart
    strategy: Strategy
    task: threading.Thread

    def __init__(self, *, table: str = '', screen: str = '', load_contracts: bool = False, quick: bool = False, exit: bool = False):
        self.table = table.upper()
        self.screen = screen
        self.load_contracts = load_contracts
        self.quick = quick
        self.exit = exit
        self.days = 1000
        self.backtest = 0
        self.results_corr = []
        self.screener = None

        abort = False

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
                ui.print_error('Exchange, index or ticker not found')

        if self.screen:
            screens = screener.get_screen_names()
            if not self.screen in screens:
                ui.print_error(f'Screen \'{self.screen}\' not found')
                abort = True
                self.screen = ''

        if abort:
            pass  # We're done
        elif self.table and self.screen:
            self.main_menu(selection=3)
        else:
            self.main_menu()

    def main_menu(self, selection: int = 0) -> None:
        while True:
            menu_items = {
                '1':  'Select Table or Index',
                '2':  'Select Screen',
                '3':  'Run Screen',
                '4':  'Run Backtest Screen',
                '5':  'Refresh Screen',
                '6':  'Run Option Strategy',
                '7':  'Run Support & Resistance Analysis',
                '8':  'Run Coorelation',
                '9':  'Show by Sector',
                '10': 'Show Top Results',
                '11': 'Show All Results',
                '12': 'Show Ticker Screen Results',
                '13': 'Show Chart',
                '14': 'Build Result Files',
                '15': 'Analyze Result Files',
                '16': 'Roll Result Files',
                '17': 'Delete Result Files',
                '0':  'Exit'
            }

            if self.table:
                menu_items['1'] += f' ({self.table})'

            if self.screen:
                menu_items['2'] += f' ({self.screen})'

            if self.backtest > 0:
                menu_items['4'] += f' ({self.backtest})'

            if self.quick:
                menu_items['7'] += ' (quick)'

            if self.screener is not None and len(self.screener.valids) > 0:
                top = len(self.screener.valids) if len(self.screener.valids) < LISTTOP_SCREEN else LISTTOP_SCREEN
                menu_items['10'] += f' ({top})'

            if self.screener is not None and len(self.screener.valids) > 0:
                menu_items['11'] += f' ({len(self.screener.valids)})'

            if selection == 0:
                selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1)

            if selection == 1:
                self.select_table()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                self.backtest = 0
                if self.run_screen():
                    if len(self.screener.valids) > 0:
                        self.show_valids(top=LISTTOP_SCREEN)
            elif selection == 4:
                if self.run_backtest():
                    if len(self.screener.valids) > 0:
                        self.show_backtest(top=LISTTOP_SCREEN)
            elif selection == 5:
                self.refresh_screen()
                if len(self.screener.valids) > 0:
                    self.show_valids(top=LISTTOP_SCREEN)
            elif selection == 6:
                self.select_option_strategy()
            elif selection == 7:
                self.select_support_resistance()
            elif selection == 8:
                self.run_coorelate()
                if len(self.results_corr) > 0:
                    self.show_coorelations()
            elif selection == 9:
                self.filter_by_sector()
            elif selection == 10:
                self.show_valids(top=LISTTOP_SCREEN)
            elif selection == 11:
                self.show_valids()
            elif selection == 12:
                self.show_ticker_results()
            elif selection == 13:
                self.show_chart()
            elif selection == 14:
                self.build_result_files()
            elif selection == 15:
                self.analyze_result_files()
            elif selection == 16:
                self.roll_result_files()
            elif selection == 17:
                self.delete_result_files()
            elif selection == 0:
                self.exit = True

            selection = 0

            if self.exit:
                break

    def select_table(self) -> None:
        list = ui.input_alphanum('Enter exchange or index').upper()
        if store.is_list(list):
            self.table = list
        else:
            self.table = ''
            ui.print_error(f'List {list} is not valid')

        if self.table and self.screen:
            self.screener = Screener(self.table, screen=self.screen)
            if self.screener.cache_available:
                self.run_screen()

    def select_screen(self) -> None:
        screens = screener.get_screen_names()
        if screens:
            menu_items = {f'{index}': f'{item.title()}' for index, item in enumerate(screens, start=1)}
            menu_items['0'] = 'Cancel'

            selection = ui.menu(menu_items, 'Available Screens', 0, len(menu_items)-1, prompt='Select screen, or 0 to cancel')
            if selection > 0:
                if self.table:
                    self.screen = screens[selection-1]
                    self.screener = Screener(self.table, screen=self.screen)
                    if self.screener.cache_available:
                        self.run_screen()
        else:
            ui.print_message('No screener files found')

    def select_option_strategy(self) -> None:
        if len(self.screener.valids) > 0:
            menu_items = {
                '1': 'Call',
                '2': 'Put',
                '3': 'Vertical',
                '4': 'Iron Condor',
                '5': 'Iron Butterfly',
                '0': 'Cancel',
            }

            modified = True
            selection = ui.menu(menu_items, 'Available Strategy', 0, len(menu_items), prompt='Select strategy, or 0 to cancel')
            if selection == 1:
                strategy = 'call'
                product = 'call'
                selection = ui.input_integer('(1) Long, or (2) Short', 1, 2)
                direction = 'long' if selection == 1 else 'short'
            elif selection == 2:
                strategy = 'put'
                product = 'put'
                selection = ui.input_integer('(1) Long, or (2) Short', 1, 2)
                direction = 'long' if selection == 1 else 'short'
            elif selection == 3:
                strategy = 'vert'
                p = ui.input_integer('(1) Call, or (2) Put: ', 1, 2)
                product = 'call' if p == 1 else 'put'
                selection = ui.input_integer('(1) Debit, or (2) Credit', 1, 2)
                direction = 'long' if selection == 1 else 'short'
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
                if self.load_contracts and d.ACTIVE_OPTIONDATASOURCE == 'etrade':
                    if auth.Session is None:
                        auth.authorize(_auth_callback)

                self.run_strategies(strategy, product, direction)
        else:
            ui.print_error('No valid results to analyze')

    def select_support_resistance(self) -> None:
        tickers = []
        ticker = ui.input_text("Enter ticker or 'valids'").upper()
        if store.is_ticker(ticker):
            tickers = [ticker]
        elif ticker != 'VALIDS':
            pass
        elif len(self.screener.valids) > 0:
            tickers = [str(result) for result in self.screener.valids[:LISTTOP_TREND]]
        else:
            ui.print_error('Not a valid ticker')

        if tickers:
            self.run_support_resistance(tickers)

    def run_screen(self, use_cache: bool = True) -> bool:
        success = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        else:
            try:
                self.screener = Screener(self.table, screen=self.screen, backtest=self.backtest)
            except ValueError as e:
                ui.print_error(f'{__name__}: {str(e)}')
            else:
                cache = False if self.backtest > 0 else use_cache
                save = (self.backtest == 0)

                self.task = threading.Thread(target=self.screener.run, kwargs={'use_cache': cache, 'save_results': save})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress_screen()

                if self.screener.task_state == 'Done':
                    self.screener.valids = self.screener.valids

                    if self.screener.cache_used:
                        ui.print_message(f'{len(self.screener.valids)} symbols identified. Cached results used')
                    else:
                        ui.print_message(f'{len(self.screener.valids)} symbols identified in {self.screener.task_time:.1f} seconds', pre_creturn=1)

                    success = True

        return success

    def run_backtest(self, prompt: bool = True, bullish: bool = True) -> bool:
        success = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        else:
            if prompt:
                input = ui.input_integer('Input number of days (10-100)', 10, 100)
                self.backtest = input

            success = self.run_screen()

            if success:
                for result in self.screener.valids:
                    if result:
                        result.price_last = result.company.get_last_price()

                        if bullish:
                            result.backtest_success = (result.price_current > result.price_last)
                        else:
                            result.backtest_success = (result.price_current < result.price_last)

                        if result.price_current <= 0.0:
                            self.screener.errors += [result]
                            self.screener.valids.remove(result)

        return success

    def refresh_screen(self):
        self.run_screen(False)

    def run_strategies(self, strategy: str, product: str, direction: str) -> None:
        if strategy not in s.STRATEGIES:
            raise ValueError('Invalid strategy')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')

        tickers = [str(result) for result in self.screener.valids[:LISTTOP_SCREEN]]

        strategies = []
        for ticker in tickers:
            if self.load_contracts:
                strike = float(math.floor(store.get_last_price(ticker)))
                width1 = width2 = 1
            else:
                strike, width1, width2 = m.calculate_strike_and_widths(strategy, product, direction, store.get_last_price(ticker))

            score_screen = self.screener.get_score(ticker)
            strategies += [sl.strategy_type(ticker=ticker, strategy=strategy, product=product,
                                            direction=direction, strike=strike, width1=width1, width2=width2, expiry=dt.datetime.now(),
                                            volatility=(-1.0, 0.0), score_screen=score_screen, load_contracts=self.load_contracts)]

        if len(strategies) > 0:
            sl.reset()
            self.task = threading.Thread(target=sl.analyze, args=[strategies])

            tic = time.perf_counter()
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress_options()

            toc = time.perf_counter()
            task_time = toc - tic

            # Show the results
            if not sl.strategy_results.empty:
                drop = ['breakeven', 'breakeven1', 'breakeven2']
                table = sl.strategy_results.drop(drop, axis=1, errors='ignore')
                strategy = table.iloc[:, :6]
                headers = headers = ui.format_headers(strategy)

                ui.print_message(f'Strategy Analysis ({task_time:.1f}s)', pre_creturn=2, post_creturn=1)
                print(tabulate(strategy, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
                print()

                summary = table.iloc[:, 6:]
                headers = headers = ui.format_headers(summary)
                print(tabulate(summary, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
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
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress_support_resistance()

                figure = self.trend.plot()
                plt.figure(figure)

            plt.show()
        else:
            ui.print_error('No valid results to analyze')

    def run_coorelate(self) -> None:
        if len(self.screener.valids) == 0:
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
            for valid in self.screener.valids:
                ticker = valid.company.ticker
                df = self.coorelate.get_ticker_coorelation(ticker)
                self.results_corr += [(ticker, df.iloc[-1])]

    def filter_by_sector(self):
        if self.screener.valids:
            sectors = store.get_sectors()
            sectors.sort()

            menu_items = {f'{index}': f'{item}' for index, item in enumerate(sectors, start=1)}
            menu_items['0'] = 'Done'

            selection = ui.menu(menu_items, 'Market Sectors', 0, len(menu_items)-1, prompt='Select desired sector')
            if selection > 0:
                valids = [str(r) for r in self.screener.valids]
                filtered = store.get_sector_tickers(valids, sectors[selection-1])

                index = 1
                ui.print_message(f'Results of {self.screen}/{self.table} for the {sectors[selection-1]} sector', post_creturn=1)
                for result in self.screener.valids:
                    if str(result) in filtered:
                        print(f'{index:>3}: {str(result):<5} {float(result):.2f} - {result.company.information["name"]}')
                        index += 1
        else:
            ui.print_message('No results were located')

    def show_valids(self, top: int = -1) -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        elif len(self.screener.valids) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
            elif top > self.screener.task_success:
                top = self.screener.task_success

            if self.backtest > 0:
                drop = ['valid', 'screen']
            else:
                drop = ['valid', 'screen', 'price_last', 'backtest_success']
            summary = screener.summarize_results(self.screener.valids).drop(drop, axis=1)
            headers = ui.format_headers(summary.columns)

            ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen.title()}/{self.table})', post_creturn=1)
            print(tabulate(summary.head(top), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

        print()

    def show_backtest(self, top: int = -1):
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        elif len(self.screener.valids) == 0:
            ui.print_message('No results were located')
        else:
            if top <= 0:
                top = self.screener.task_success
            elif top > self.screener.task_success:
                top = self.screener.task_success

            summary = screener.summarize_results(self.screener.valids)
            successes = summary[summary.backtest_success == True]

            total = summary.shape[0]
            rows = successes.shape[0]
            successful = float(rows) / total

            order = ['ticker', 'score', 'backtest_success', 'price_last', 'price_current']
            successes = successes.reindex(columns=order)
            headers = ui.format_headers(successes.columns)

            ui.print_message(f'Backtest Results: {top} of {self.screener.task_success} screened ({self.screen.title()}) Success = {successful*100:.2f}% ({rows}/{total})', post_creturn=1)
            if successful > 0:
                print(tabulate(successes.head(top), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))
            else:
                ui.print_message(f'None', post_creturn=1)

            if self.screener.errors:
                summary = screener.summarize_results(self.screener.errors)
                errors = summary.reindex(columns=order)
                ui.print_message('Backtest Errors', post_creturn=1)
                print(tabulate(errors, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

    def show_chart(self):
        ticker = ui.input_text("Enter ticker").upper()
        if store.is_ticker(ticker):
            self.chart = Chart(ticker, days=180)

            self.task = threading.Thread(target=self.chart.fetch_history)
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress_chart()

            figure = self.chart.plot_ohlc()
            plt.figure(figure)
            plt.show()
        else:
            ui.print_error('Not a valid ticker')

    def show_ticker_results(self):
        ticker = ui.input_text('Enter ticker').upper()
        if ticker:
            ui.print_message('Ticker Screen Results')
            for result in self.screener.results:
                [print(r) for r in result.descriptions if ticker.ljust(6, ' ') == r[:6]]

    def show_coorelations(self):
        results = [f'{result[0]:<5}/ {result[1]["ticker"]:<5} {result[1]["value"]:.5f}' for result in self.results_corr if result[1]['value'] > COOR_CUTOFF]
        if results:
            ui.print_message('Coorelation Results')
            for result in results[:LISTTOP_CORR]:
                print(result)
        else:
            ui.print_message('No significant coorelations found')

    def show_progress_screen(self) -> None:
        while not self.screener.task_state:
            pass

        if self.screener.task_state == 'None':
            prefix = f'Screening {self.table}/{self.screen.title()}'
            if self.backtest > 0:
                prefix += f' (-{self.backtest} days)'
            total = self.screener.task_total
            ui.progress_bar(self.screener.task_completed, self.screener.task_total, prefix=prefix, reset=True)

            while self.screener.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                completed = self.screener.task_completed
                success = self.screener.task_success
                ticker = self.screener.task_ticker
                tasks = len([True for future in self.screener.task_futures if future.running()])

                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success, tasks=tasks)

    def show_progress_options(self) -> None:
        while not sl.strategy_state:
            pass

        prefix = 'Creating Strategies'
        ui.progress_bar(0, 0, prefix=prefix, reset=True)
        if sl.strategy_state == 'None':
            while sl.strategy_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                ui.progress_bar(0, 0, prefix=prefix, suffix=sl.strategy_msg)

            if sl.strategy_state == 'Next':
                prefix = 'Analyzing Strategies'
                ui.erase_line()
                ui.progress_bar(0, 0, prefix=prefix)

                while sl.strategy_state == 'Next':
                    time.sleep(ui.PROGRESS_SLEEP)

                    # Catch case of a task exception not allowing normal completion
                    tasks = len([True for future in sl.strategy_futures if future.running()])
                    if tasks == 0:
                        break

                    ui.progress_bar(sl.strategy_completed, sl.strategy_total, prefix=prefix, suffix='', tasks=tasks)

    def show_progress_support_resistance(self) -> None:
        while not self.trend.task_state:
            pass

        if self.trend.task_state == 'History':
            prefix = 'Retrieving History'
            ui.progress_bar(0, 0, prefix=prefix, reset=True)
            while self.trend.task_state == 'History':
                time.sleep(ui.PROGRESS_SLEEP)
                ui.progress_bar(0, 0, prefix=prefix, suffix=self.trend.task_message)

        if self.trend.task_state == 'None':
            prefix = 'Analyzing S & R'
            while self.trend.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                ui.progress_bar(0, 0, prefix=prefix, suffix=self.trend.task_message)

            if self.trend.task_state == 'Done':
                ui.print_message(f'{self.trend.task_state}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds', pre_creturn=2)
            else:
                ui.print_error(f'{self.trend.task_state}: Error extracting lines', pre_creturn=1)
        else:
            ui.print_message(f'{self.trend.task_state}')

        print()

    def show_progress_correlate(self):
        while not self.coorelate.task_state:
            pass

        if self.coorelate.task_state == 'None':
            prefix = 'Correlating'
            total = self.coorelate.task_total
            ui.progress_bar(self.coorelate.task_completed, self.coorelate.task_total, success=self.coorelate.task_success, prefix=prefix, reset=True)

            while self.task.is_alive() and self.coorelate.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                completed = self.coorelate.task_completed
                success = completed
                ticker = self.coorelate.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=success)

        print()

    def show_progress_chart(self) -> None:
        while not self.chart.task_state:
            pass

        if self.chart.task_state == 'None':
            prefix = 'Fetching history'
            ui.progress_bar(0, 0, prefix=prefix, reset=True)

            while self.chart.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                ui.progress_bar(0, 0, prefix=prefix, suffix=self.chart.task_ticker)

        print()

    def build_result_files(self) -> None:
        screens = screener.get_screen_names()
        screens.sort()

        tables = store.get_exchanges()
        tables.extend(store.get_indexes())
        tables += ['EVERY']
        tables.sort()

        for screen in screens:
            for table in tables:
                self.screen = screen
                self.table = table
                self.run_screen(use_cache=False)

    def analyze_result_files(self):
        if self.table:
            summary, multiples = screener.analyze_results(self.table)

            # Top scores
            headers = ui.format_headers(summary.columns)
            top = LISTTOP_ANALYSIS if len(summary) > LISTTOP_ANALYSIS else len(summary)
            ui.print_message(f'Top {top} of {len(summary)} Scores of {self.table.upper()}', post_creturn=1)
            print(tabulate(summary.head(LISTTOP_ANALYSIS), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

            if not multiples.empty:
                headers = ui.format_headers(multiples.columns)
                ui.print_message('Successes Across Multiple Screens', post_creturn=1)
                print(tabulate(multiples, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

        else:
            ui.print_error('No exchange or index specified')

    def roll_result_files(self) -> None:
        success, message = cache.roll(screener.CACHE_TYPE)
        if success:
            ui.print_message(message)
        else:
            ui.print_error(message)

    def delete_result_files(self):
        select = ui.input_text('Delete files? (y/n)').lower()
        if select == 'y':
            success, message = cache.delete(screener.CACHE_TYPE)
            if success:
                ui.print_message(message)
            else:
                ui.print_error(message)
        else:
            ui.print_message('Nothing deleted')



def main():
    parser = argparse.ArgumentParser(description='Screener')
    parser.add_argument('-t', '--table', help='Specify a symbol or table', metavar='table', required=False, default='')
    parser.add_argument('-s', '--screen', help='Specify a screening script', metavar='script', required=False, default='')
    parser.add_argument('-f', '--default', help='Load the default options', required=False, action='store_true')
    parser.add_argument('-q', '--quick', help='Run a quick analysis', action='store_true')
    parser.add_argument('-x', '--exit', help='Run the script and quit (only valid with -t and -s) then exit', action='store_true')

    command = vars(parser.parse_args())

    Interface(table=command['table'], screen=command['screen'], load_contracts=command['default'], quick=command['quick'], exit=command['exit'])


if __name__ == '__main__':
    main()
