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


class Interface:
    def __init__(self, table: str = '', screen: str = '', backtest: int = 0, exit: bool = False, live: bool = False):
        self.table = table.upper()
        self.screen = screen
        self.exit = exit
        self.live = live if store.is_database_connected() else True
        self.auto = False
        self.valids: list[Result] = []
        self.commands: list[dict] = []
        self.source = 'live' if live else d.ACTIVE_DB
        self.screener: Screener
        self.task: threading.Thread

        abort = False

        if type(backtest) == int:
            self.backtest = backtest
        else:
            self.backtest = 0
            abort = False
            ui.print_error('\'backtest\' must be an integer. Using a value of 0')

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

        if self.screen:
            screens = screener.get_screen_names()
            if not self.screen in screens:
                ui.print_error(f'Screen \'{self.screen}\' not found')
                abort = True
                self.screen = ''

        if abort:
            pass
        elif self.table and self.screen:
            self.main_menu(selection=4)
        else:
            self.main_menu()

    def main_menu(self, selection: int = 0) -> None:
        self.commands = [
            {'menu': 'Select Data Source', 'function': self.m_select_source, 'condition': 'True', 'value': 'self.source'},
            {'menu': 'Select List', 'function': self.m_select_list, 'condition': 'self.table', 'value': 'self.table'},
            {'menu': 'Select Screener', 'function': self.m_select_screen, 'condition': 'self.screen', 'value': 'self.screen'},
            {'menu': 'Run Screen', 'function': self.m_run_screen, 'condition': '', 'value': ''},
            {'menu': 'Run Backtest', 'function': self.run_backtest, 'condition': '', 'value': ''},
            {'menu': 'Show Ticker Screener Results', 'function': self.m_print_ticker_results, 'condition': '', 'value': ''},
            {'menu': 'Show Valids', 'function': self.m_show_valids, 'condition': 'len(self.valids)>0', 'value': 'len(self.valids)'},
        ]

        # Create the menu
        menu_items = {str(i+1): f'{cmd["menu"]}' for i, cmd in enumerate(self.commands)}

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while not self.exit:
            update(menu_items)

            if selection == 0:
                selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))

            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                self.exit = True

            selection = 0

            if self.exit:
                break

    def m_select_source(self) -> None:
        menu_items = {
            '1': 'Database',
            '2': 'Live',
        }

        selection = ui.menu(menu_items, 'Available Data Sources', 0, len(menu_items), prompt='Select source, or 0 when done', cancel='Done')
        if selection == 1:
            self.live = False
        elif selection == 2:
            self.live = True

    def m_select_list(self) -> None:
        list = ui.input_table(True, True, True, True).upper()
        if list:
            self.table = list
        else:
            self.table = ''
            ui.print_error(f'List {list} is not valid')

    def m_select_screen(self) -> None:
        self.script = []
        self.valids = []
        screens = screener.get_screen_names()
        if screens:
            menu_items = {f'{index}': f'{item.title()}' for index, item in enumerate(screens, start=1)}

            selection = ui.menu(menu_items, 'Available Screens', 0, len(menu_items), prompt='Select screen, or 0 to cancel', cancel = 'Cancel')
            if selection > 0:
                if self.table:
                    self.screen = screens[selection-1]
                    self.screener = Screener(self.table, screen=self.screen)
                    if self.screener.cache_available:
                        self.run_screen()

        else:
            ui.print_message('No screener files found')

    def m_run_screen(self):
        self.run_screen()
        if len(self.valids) > 0:
            self.m_show_valids()

    def run_screen(self) -> bool:
        success = False
        self.auto = False

        if not self.table:
            ui.print_error('No exchange, index, or ticker specified')
        elif not self.screen:
            ui.print_error('No screen specified')
        else:
            if self.backtest > 0:
                self.live = False

            try:
                self.screener = Screener(self.table, screen=self.screen, backtest=self.backtest, live=self.live)
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

                    if self.screener.cache_used:
                        ui.print_message(f'{len(self.screener.valids)} symbols identified. Cached results from {self.screener.cache_date} used')
                    else:
                        ui.print_message(f'{len(self.screener.valids)} symbols identified in {self.screener.task_time:.1f} seconds', pre_creturn=1)

                    success = True

        return success

    def m_run_backtest(self, prompt: bool = True, bullish: bool = True) -> bool:
        if self.run_backtest(prompt=not self.auto):
            if len(self.valids) > 0:
                self.show_backtest()

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

    def m_show_valids(self, top: int = 20, ticker: str = '') -> None:
        if not self.table:
            ui.print_error('No table specified')
        elif not self.screen:
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
                ui.print_message(f'Screener Results for {ticker} ({self.screen})')
            else:
                ui.print_message(f'Screener Results {top} of {self.screener.task_success} ({self.screen})', post_creturn=1)

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
        elif not self.screen:
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

            ui.print_message(f'Backtest Results {top} of {self.screener.task_success} ({self.screen})')
            print(tabulate(summary.head(top), headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

    def m_print_ticker_results(self):
        ticker = ui.input_text('Enter ticker')
        if ticker:
            ticker = ticker.upper()
            if store.is_ticker(ticker):
                self.m_show_valids(ticker=ticker)

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
