import logging
import time
import threading

import data as d
from data import store as store
from data import manager as manager
from utils import utils as utils

logger = utils.get_logger(logging.WARNING)


class Interface:
    def __init__(self, ticker:str='', update:str=''):
        exit = False
        self.ticker = ''
        self.stop = False

        if ticker:
            if store.is_ticker(ticker.upper()):
                self.ticker = ticker.upper()
                self.stop = True
            else:
                exit = True
                utils.print_error(f'Invalid ticker specifed: {ticker}')
        elif update:
            if store.is_ticker(update.upper()):
                self.ticker = update.upper()
                self.stop = True
            else:
                exit = True
                utils.print_error(f'Invalid ticker specifed: {update}')

        self.exchanges:list[str] = [e['abbreviation'] for e in d.EXCHANGES]
        self.indexes:list[str] = [i['abbreviation'] for i in d.INDEXES]
        self.manager:manager.Manager = manager.Manager()
        self.task:threading.Thread = None

        if exit:
            pass
        elif ticker:
            self.main_menu(selection=2)
        elif update:
            self.main_menu(selection=4)
        else:
            self.main_menu()

    def main_menu(self, selection=0):
        if not self.stop:
            self.show_database_information()

        menu_items = {
            '1': 'Database Information',
            '2': 'Ticker Information',
            '3': 'Ticker Information (prev)',
            '4': 'Ticker Information (live)',
            '5': 'List Exchange',
            '6': 'List Index',
            '7': 'Populate Exchange',
            '8': 'Populate Index',
            '9': 'Update Ticker(s)',
            '10': 'Check Integrity',
            '11': 'Delete Exchange',
            '12': 'Delete Index',
            '13': 'Delete Ticker',
            '14': 'Reset Database',
            '0': 'Exit'
        }

        while True:
            if not self.ticker:
                selection = utils.menu(menu_items, 'Select Operation', 0, 14)

            if selection == 1:
                self.show_database_information()
            elif selection == 2:
                self.show_symbol_information(self.ticker)
            elif selection == 3:
                self.show_symbol_information(self.ticker, prompt=True)
            elif selection == 4:
                self.show_symbol_information(self.ticker, live=True)
            elif selection == 5:
                self.list_exchange()
            elif selection == 6:
                self.list_index()
            elif selection == 7:
                self.populate_exchange()
            elif selection == 8:
                self.populate_index()
            elif selection == 9:
                self.update_ticker(self.ticker)
            elif selection == 10:
                self.check_integrity()
            elif selection == 11:
                self.delete_exchange()
            elif selection == 12:
                self.delete_index()
            elif selection == 13:
                self.delete_ticker()
            elif selection == 14:
                self.reset_database()
            elif selection == 0:
                break

            if self.stop:
                break

    def show_database_information(self):
        utils.print_message(f'Database Information ({d.ACTIVE_DB})')
        info = self.manager.get_database_info()
        for i in info:
            print(f'{i["table"]:>16}:\t{i["count"]} records')

        utils.print_message('Exchange Information')
        info = self.manager.get_exchange_info()
        for i in info:
            print(f'{i["exchange"]:>16}:\t{i["count"]} symbols')

        utils.print_message('Index Information')
        info = self.manager.get_index_info()
        for i in info:
            print(f'{i["index"]:>16}:\t{i["count"]} symbols')

    def show_symbol_information(self, ticker:str ='', prompt:bool=False, live:bool=False):
        if not ticker:
            ticker = utils.input_text('Enter ticker: ').upper()

        if ticker:
            if store.is_ticker(ticker):
                if prompt:
                    end = utils.input_integer('Input number of days: ', 0, 100)
                else:
                    end=0

                company = store.get_company(ticker, live=live, extra=True)
                if company:
                    if live:
                        utils.print_message(f'{ticker} Company Information (live)')
                    else:
                        utils.print_message(f'{ticker} Company Information')

                    print(f'Name:\t\t{company["name"]}')

                    if not live:
                        print(f'Exchange:\t{company["exchange"]}')
                    else:
                        print(f'Exchange:\t{store.get_ticker_exchange(ticker)}')

                    print(f'Market Cap:\t{company["marketcap"]:,}')
                    print(f'Beta:\t\t{company["beta"]:.2f}')
                    print(f'Rating:\t\t{company["rating"]:.2f}')

                    if not live:
                        print(f'Indexes:\t{company["indexes"]}')
                    else:
                        print(f'Indexes:\t{store.get_ticker_index(ticker)}')

                    print(f'Sector:\t\t{company["sector"]}')
                    print(f'Industry:\t{company["industry"]}')
                    print(f'URL:\t\t{company["url"]}')

                    if not live:
                        print(f'Price Records:\t{company["precords"]}')
                        print(f'Active:\t\t{company["active"]}')
                else:
                    utils.print_error(f'{ticker} has no company information')

                history = store.get_history(ticker, 100, end=end, live=live).round(2)
                if history.empty:
                    utils.print_error(f'{ticker} has no price history')
                else:
                    if not live:
                        latest = history.iloc[-1]
                        print(f'Latest Record:\t{latest["date"]:%Y-%m-%d}, closed at ${latest["close"]:.2f}')

                    utils.print_message(f'{ticker} Recent Price History')
                    history = history.tail(10)
                    if not history.empty:
                        history.set_index('date', inplace=True)
                        print(history.round(2))

            else:
                utils.print_error(f'{ticker} not found')

    def list_exchange(self):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.exchanges))
        if select > 0:
            exc = self.exchanges[select-1]
            found = self.manager.list_exchange(exc)

            if len(found) > 0:
                print()
                index = 0
                for ticker in found:
                    print(f'{ticker} ', end='')
                    index += 1
                    if index % 20 == 0: # Print 20 per line
                        print()
                print()
            else:
                utils.print_message(f'No tickers in exchange {exc}')

    def list_index(self):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            ind = self.indexes[select-1]
            found = self.manager.list_index(ind)

            if len(found) > 0:
                print()
                index = 0
                for ticker in found:
                    print(f'{ticker} ', end='')
                    index += 1
                    if index % 20 == 0: # Print 20 per line
                        print()
                print()
            else:
                utils.print_message(f'No tickers in index {ind}')

    def populate_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.exchanges))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.populate_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_success} {exc} '\
                    f'Symbols populated in {self.manager.task_time/60.0:.1f} minutes with {len(self.manager.invalid_tickers)} invalid symbols')

    def populate_index(self, progressbar=True):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            self.task = threading.Thread(target=self.manager.populate_index, args=[self.indexes[select-1]])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_success} {self.indexes[select-1]} Symbols populated in {self.manager.task_time:.0f} seconds')
            else:
                utils.print_error(self.manager.task_error)

    def refresh_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        exchange = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.indexes))
        if exchange > 0:
            exc = self.exchanges[exchange-1]
            self.task = threading.Thread(target=self.manager.refresh_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            print()
            utils.print_message(f'Identified {self.manager.task_total} missing items. {self.manager.task_success} items filled')

    def update_ticker(self, ticker:str ='', progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items[f'{i+2}'] = 'All'
        menu_items[f'{i+3}'] = 'Ticker'
        menu_items['0'] = 'Cancel'

        if not ticker:
            select = utils.menu(menu_items, 'Select table, or 0 to cancel: ', 0, len(self.exchanges)+2)
        else:
            select = 5

        if select == 5:
            if not ticker:
                ticker = input('Please enter symbol, or 0 to cancel: ').upper()

            if ticker != '0':
                if store.is_ticker(ticker):
                    days = self.manager.update_history_ticker(ticker)
                    utils.print_message(f'Added {days} days pricing for {ticker}')
                    self.show_symbol_information(ticker=ticker)
                elif store.get_ticker_exchange(ticker):
                    exchange = store.get_ticker_exchange(ticker)
                    if self.manager.add_securities_to_exchange([ticker], exchange):
                        utils.print_message(f'Added {ticker} to {exchange}')
                        self.show_symbol_information(ticker=ticker)
                    else:
                        utils.print_error(f'Error adding {ticker} to {exchange}')

                else:
                    utils.print_error('Invalid ticker. Try another ticker or select "0" to cancel')
        elif select > 0:
            exc = self.exchanges[select-1] if select <= len(self.exchanges) else ''
            self.task = threading.Thread(target=self.manager.update_history_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_total} {exc} '\
                    f'Ticker pricing refreshed in {self.manager.task_time:.0f} seconds')

    def delete_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.delete_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('', '')

            self.create_missing_tables()

            if self.manager.task_error == 'Done':
                utils.print_message(f'Deleted exchange {exc} in {self.manager.task_time:.0f} seconds')

    def delete_index(self):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(self.indexes))
        if select > 0:
            ind = self.indexes[select-1]
            self.manager.delete_index(ind)
            self.create_missing_tables()

            utils.print_message(f'Deleted exchange {ind}')

    def delete_ticker(self, ticker:str=''):
        if not ticker:
            ticker = utils.input_text('Enter ticker: ').upper()

        if ticker:
            if store.is_ticker(ticker):
                self.manager.delete_ticker(ticker)

                utils.print_message(f'Deleted ticker {ticker}')

    def reset_database(self):
        select = utils.input_integer('Are you sure? 1 to reset or 0 to cancel: ', 0, 1)
        if select == 1:
            self.manager.delete_database()
            self.manager.create_database()
            self.manager.create_exchanges()
            self.manager.create_indexes()
            utils.print_message(f'Database is reset')
        else:
            utils.print_message('Database not reset')

    def check_integrity(self):
        exchanges = store.get_exchanges()
        utils.print_message('Missing Tickers')
        for e in exchanges:
            count = len(self.manager.identify_missing_securities(e))
            print(f'{e:>16}:\t{count}')

        utils.print_message('Incomplete Companies')
        for e in exchanges:
            missing = self.manager.identify_incomplete_companies(e)
            print(f'{e:>16}:\t{len(missing)}')

        utils.print_message('Incomplete Pricing')
        for e in exchanges:
            count = len(self.manager.identify_incomplete_pricing(e))
            print(f'{e:>16}:\t{count}')

    def create_missing_tables(self):
        self.manager.create_exchanges()
        self.manager.create_indexes()

    def list_invalid(self):
        utils.print_message(f'Invalid: {self.manager.invalid_tickers}')

    def _show_progress(self, prefix, suffix):
        while not self.manager.task_error: pass

        if self.manager.task_error == 'None':
            utils.progress_bar(self.manager.task_completed, self.manager.task_total, prefix=prefix, suffix=suffix, length=50, reset=True)
            while self.task.is_alive and self.manager.task_error == 'None':
                time.sleep(0.20)
                total = self.manager.task_total
                completed = self.manager.task_completed
                success = self.manager.task_success
                symbol = self.manager.task_ticker
                tasks = len([True for future in self.manager.task_futures if future.running()])

                if total > 0:
                    utils.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=symbol, length=50, success=success, tasks=tasks)
                else:
                    utils.progress_bar(completed, total, prefix=prefix, suffix='', length=50)

            results = [future.result() for future in self.manager.task_futures if future.result() is not None]
            if len(results) > 0:
                utils.print_message('Processed Messages')
                [print(result) for result in results]
        else:
            utils.print_message(f'{self.manager.task_error}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database Management')
    parser.add_argument('-t', '--ticker', help='Get ticker information', required=False)
    parser.add_argument('-u', '--update', help='Update ticker', required=False)

    command = vars(parser.parse_args())

    if command['ticker']:
        Interface(ticker=command['ticker'])
    elif command['update']:
        Interface(update=command['update'])
    else:
        Interface()

