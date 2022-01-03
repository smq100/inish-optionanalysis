import logging
import time
import threading

import data as d
from data import store as store
from data import manager as manager
from utils import ui


_logger = ui.get_logger(logging.WARNING, logfile='output')


class Interface:
    def __init__(self, ticker:str='', update:str='', quick:bool=False):
        exit = False
        self.ticker = ''
        self.quick = quick
        self.stop = False

        if store.is_database_connected():
            if ticker:
                if store.is_ticker(ticker.upper()):
                    self.ticker = ticker.upper()
                    self.stop = True
                else:
                    exit = True
                    ui.print_error(f'Invalid ticker specifed: {ticker}')
            elif update:
                if store.is_ticker(update.upper()):
                    self.ticker = update.upper()
                    self.stop = True
                else:
                    exit = True
                    ui.print_error(f'Invalid ticker specifed: {update}')

            self.exchanges:list[str] = store.get_exchanges()
            self.indexes:list[str] = store.get_indexes()
            self.manager:manager.Manager = manager.Manager()
            self.task:threading.Thread = None

            if not store.is_live_connection():
                ui.print_error('No Internet connection')

            if exit:
                pass
            elif ticker:
                self.main_menu(selection=2)
            elif update:
                self.main_menu(selection=4)
            else:
                self.main_menu()
        else:
            ui.print_error('No databases available')

    def main_menu(self, selection:int=0) -> None:
        if not self.stop and not self.quick:
            self.show_database_information()

        menu_items = {
            '1': 'Database Information',
            '2': 'Ticker Information',
            '3': f'Ticker Information ({d.ACTIVE_DATASOURCE})',
            '4': 'Ticker Information (previous)',
            '5': 'List Table',
            '6': 'Update History',
            '7': 'Update Company',
            '8': 'Check Integrity',
            '9': 'Check Price Dates',
            '10': 'Populate Exchange',
            '11': 'Populate Index',
            '12': 'Delete Exchange',
            '13': 'Delete Index',
            '14': 'Delete Ticker',
            '15': 'Reset Database',
            '0': 'Exit'
        }

        while True:
            if not self.ticker:
                selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.show_database_information()
            elif selection == 2:
                self.show_symbol_information(self.ticker)
            elif selection == 3:
                self.show_symbol_information(self.ticker, live=True)
            elif selection == 4:
                self.show_symbol_information(self.ticker, prompt=True)
            elif selection == 5:
                self.list_table()
            elif selection == 6:
                self.update_history(self.ticker)
            elif selection == 7:
                self.update_company()
            elif selection == 8:
                self.check_integrity()
            elif selection == 9:
                self.check_price_dates()
            elif selection == 10:
                self.populate_exchange()
            elif selection == 11:
                self.populate_index()
            elif selection == 12:
                self.delete_exchange()
            elif selection == 13:
                self.delete_index()
            elif selection == 14:
                self.delete_ticker()
            elif selection == 15:
                self.reset_database()
            elif selection == 0:
                self.stop = True

            if self.stop:
                break

    def show_database_information(self) -> None:
        ui.print_message(f'Database Information ({d.ACTIVE_DB})')
        info = self.manager.get_database_info()
        for i in info: print(f'{i["table"]:>16}:\t{i["count"]} records')

        ui.print_message('Exchange Information')
        info = self.manager.get_exchange_info()
        for i in info: print(f'{i["exchange"]:>16}:\t{i["count"]} symbols')

        ui.print_message('Index Information')
        info = self.manager.get_index_info()
        for i in info: print(f'{i["index"]:>16}:\t{i["count"]} symbols')

    def show_symbol_information(self, ticker:str ='', prompt:bool=False, live:bool=False) -> None:
        if not ticker:
            ticker = ui.input_text('Enter ticker: ').upper()

        if ticker:
            if store.is_ticker(ticker):
                if prompt:
                    end = ui.input_integer('Input number of days: ', 0, 100)
                else:
                    end=0

                company = store.get_company(ticker, live=live, extra=True)
                if company:
                    if live:
                        ui.print_message(f'{ticker} Company Information (live)')
                    else:
                        ui.print_message(f'{ticker} Company Information')

                    print(f'Name:\t\t{company["name"]}')

                    if not live:
                        print(f'Exchange:\t{company["exchange"]}')
                    else:
                        print(f'Exchange:\t{store.get_ticker_exchange(ticker)}')

                    if not live:
                        print(f'Indexes:\t{company["indexes"]}')
                    else:
                        print(f'Indexes:\t{store.get_ticker_index(ticker)}')

                    print(f'Market Cap:\t{company["marketcap"]:,}')
                    print(f'Beta:\t\t{company["beta"]:.2f}')
                    print(f'Rating:\t\t{company["rating"]:.2f}')

                    print(f'Sector:\t\t{company["sector"]}')
                    print(f'Industry:\t{company["industry"]}')
                    print(f'URL:\t\t{company["url"]}')

                    if not live:
                        print(f'Price Records:\t{company["precords"]}')
                        print(f'Active:\t\t{company["active"]}')
                else:
                    ui.print_error(f'{ticker} has no company information')

                history = store.get_history(ticker, days=100, end=end, live=live)
                if history is None or history.empty:
                    ui.print_error(f'{ticker} has no price history')
                else:
                    history = history.round(2)
                    if not live:
                        latest = history.iloc[-1]
                        print(f'Latest Record:\t{latest["date"]:%Y-%m-%d}, closed at ${latest["close"]:.2f}')

                    ui.print_message(f'{ticker} Recent Price History')
                    history = history.tail(10)
                    if not history.empty:
                        history.set_index('date', inplace=True)
                        print(history.round(2))

            else:
                ui.print_error(f'{ticker} not found')

    def list_table(self) -> None:
        found = []
        select = ui.input_text('Enter exchange or index: ').upper()
        if store.is_exchange(select):
            found = self.manager.list_exchange(select)
        elif store.is_list(select):
            found = self.manager.list_index(select)
        else:
            ui.print_error(f'List {select} is not valid')

        if found:
            print()
            index = 0
            for ticker in found:
                print(f'{ticker} ', end='')
                index += 1
                if index % 20 == 0: # Print 20 per line
                    print()
            print()

    def populate_exchange(self, progressbar:bool=True) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.exchanges))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.populate_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            if self.manager.task_error == 'Done':
                ui.print_message(f'{self.manager.task_success} {exc} '\
                    f'Symbols populated in {self.manager.task_time/60.0:.1f} minutes with {len(self.manager.invalid_tickers)} invalid symbols')

    def populate_index(self, progressbar:bool=True) -> None:
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            self.task = threading.Thread(target=self.manager.populate_index, args=[self.indexes[select-1]])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            if self.manager.task_error == 'Done':
                ui.print_message(f'{self.manager.task_success} {self.indexes[select-1]} Symbols populated in {self.manager.task_time:.0f} seconds')
            else:
                ui.print_error(self.manager.task_error)

    def refresh_exchange(self, progressbar:bool=True) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        selection = ui.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.indexes))
        if selection > 0:
            exc = self.exchanges[selection-1]
            self.task = threading.Thread(target=self.manager.refresh_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            print()
            ui.print_message(f'Identified {self.manager.task_total} missing items. {self.manager.task_success} items filled')

    def update_history(self, ticker:str='', progressbar:bool=True) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items[f'{i+2}'] = 'All'
        menu_items[f'{i+3}'] = 'Ticker'
        menu_items['0'] = 'Cancel'

        if not ticker:
            select = ui.menu(menu_items, 'Select option, or 0 to cancel: ', 0, len(self.exchanges)+2)
        else:
            select = 5

        if select == 5: # Update/add single ticker
            if not ticker:
                ticker = input('Please enter symbol, or 0 to cancel: ').upper()

            if ticker != '0':
                if store.is_ticker(ticker):
                    days = self.manager.update_history_ticker(ticker)
                    ui.print_message(f'Added {days} days pricing for {ticker}')
                    self.show_symbol_information(ticker=ticker)
                elif store.is_exchange(ticker):
                    exchange = store.get_ticker_exchange(ticker)
                    if self.manager.add_security_to_exchange(ticker, exchange):
                        ui.print_message(f'Added {ticker} to {exchange}')
                        self.show_symbol_information(ticker=ticker)
                    else:
                        ui.print_error(f'Error adding {ticker} to {exchange}')
                else:
                    ui.print_error('Invalid ticker. Try another ticker or select "0" to cancel')
        elif select > 0:
            exc = self.exchanges[select-1] if select <= len(self.exchanges) else 'all'
            self.task = threading.Thread(target=self.manager.update_history_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            if self.manager.task_error == 'Done':
                ui.print_message(f'{self.manager.task_total} {exc} '\
                    f'Ticker pricing refreshed in {self.manager.task_time:.0f} seconds')

    def update_company(self, ticker:str='', progressbar:bool=True) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items[f'{i+2}'] = 'All'
        menu_items[f'{i+3}'] = 'Ticker'
        menu_items['0'] = 'Cancel'

        if not ticker:
            select = ui.menu(menu_items, 'Select option, or 0 to cancel: ', 0, len(self.exchanges)+2)
        else:
            select = 5

        if select == 5: # Update/add single ticker
            if not ticker:
                ticker = input('Please enter symbol, or 0 to cancel: ').upper()

            if ticker != '0':
                if store.is_ticker(ticker):
                    if self.manager.update_company_ticker(ticker):
                        ui.print_message('Success')
                        self.show_symbol_information(ticker)
                    else:
                        ui.print_error('Error')
                else:
                    ui.print_error('Invalid ticker. Try another ticker or select "0" to cancel')
        elif select > 0:
            exc = self.exchanges[select-1] if select <= len(self.exchanges) else 'all'
            self.task = threading.Thread(target=self.manager.update_companies_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            if self.manager.task_error == 'Done':
                ui.print_message(f'{self.manager.task_total} {exc} '\
                    f'Company infomation refreshed in {self.manager.task_time:.0f} seconds')

    def delete_exchange(self, progressbar:bool=True) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.delete_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('', '')

            self.create_missing_tables()

            if self.manager.task_error == 'Done':
                ui.print_message(f'Deleted exchange {exc} in {self.manager.task_time:.0f} seconds')

    def delete_index(self) -> None:
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            ind = self.indexes[select-1]
            self.manager.delete_index(ind)
            self.create_missing_tables()

            ui.print_message(f'Deleted exchange {ind}')

    def delete_ticker(self, ticker:str='') -> None:
        if not ticker:
            ticker = ui.input_text('Enter ticker: ').upper()

        if ticker:
            if store.is_ticker(ticker):
                self.manager.delete_ticker(ticker)

                ui.print_message(f'Deleted ticker {ticker}')

    def reset_database(self) -> None:
        select = ui.input_integer('Are you sure? 1 to reset or 0 to cancel: ', 0, 1)
        if select == 1:
            self.manager.delete_database()
            self.manager.create_database()
            self.manager.create_exchanges()
            self.manager.create_indexes()
            ui.print_message(f'Database is reset')
        else:
            ui.print_message('Database not reset')

    def check_integrity(self) -> None:
        ui.print_message('Missing Tickers')
        missing_tickers = {e: self.manager.identify_missing_securities(e) for e in self.exchanges}
        for e in self.exchanges: print(f'{e:>16}:\t{len(missing_tickers[e])}')

        ui.print_message('Incomplete Companies')
        incomplete_companies = {e: self.manager.identify_incomplete_companies(e) for e in self.exchanges}
        for e in self.exchanges: print(f'{e:>16}:\t{len(incomplete_companies[e])}')

        while True:
            menu_items = {
                '1': 'List Missing Companies',
                '2': 'List Incomplete Companies',
                '0': 'Exit',
            }
            op = ui.menu(menu_items, 'Select Operation', 0, 3)

            if op > 0:
                menu_items = {}
                for i, exc in enumerate(self.exchanges):
                    menu_items[f'{i+1}'] = f'{exc}'
                menu_items['0'] = 'Cancel'
                exchange = ui.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.exchanges))

                if exchange > 0:
                    if op == 1:
                        self._list_tickers(missing_tickers[menu_items[str(exchange)]])
                    elif op == 2:
                        self._list_tickers(incomplete_companies[menu_items[str(exchange)]])
            else:
                break

    def check_price_dates(self) -> None:
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.exchanges))
        if select > 0:
            incomplete = self.manager.identify_incomplete_pricing(menu_items[str(select)])
            print(incomplete)

    def create_missing_tables(self) -> None:
        self.manager.create_exchanges()
        self.manager.create_indexes()

    def _list_tickers(self, tickers:list[str]) -> None:
        if len(tickers) > 0:
            index = 0
            print()
            for ticker in tickers:
                print(f'{ticker} ', end='')
                index += 1
                if index % 20 == 0: # Print 20 per line
                    print()
            print()

    def _show_progress(self, prefix:str, suffix:str) -> None:
        while not self.manager.task_error: pass

        if self.manager.task_error == 'None':
            ui.progress_bar(self.manager.task_completed, self.manager.task_total, prefix=prefix, suffix=suffix, reset=True)
            while self.task.is_alive and self.manager.task_error == 'None':
                time.sleep(0.20)
                total = self.manager.task_total
                completed = self.manager.task_completed
                success = self.manager.task_success
                symbol = self.manager.task_ticker
                tasks = len([True for future in self.manager.task_futures if future.running()])

                if total > 0:
                    ui.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=symbol, success=success, tasks=tasks)
                else:
                    ui.progress_bar(completed, total, prefix=prefix)

            results = [future.result() for future in self.manager.task_futures if future.result() is not None]
            if len(results) > 0:
                ui.print_message('Processed Messages')
                for result in results: print(result)
        else:
            ui.print_message(f'{self.manager.task_error}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database Management')
    parser.add_argument('-t', '--ticker', help='Get ticker information', required=False)
    parser.add_argument('-u', '--update', help='Update ticker', required=False)
    parser.add_argument('-q', '--quick', help='Start without database info', action='store_true')

    command = vars(parser.parse_args())

    if command['ticker']:
        Interface(ticker=command['ticker'], quick=command['quick'])
    elif command['update']:
        Interface(update=command['update'], quick=command['quick'])
    else:
        Interface(quick=command['quick'])

