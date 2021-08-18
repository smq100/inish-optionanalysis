import logging
import time
import threading

import data as d
from data import store as store
from data import manager as manager
from utils import utils as utils

logger = utils.get_logger(logging.WARNING)


class Interface:
    def __init__(self, ticker='', update=''):
        self.ticker = ''
        self.stop = False
        if ticker:
            if store.is_ticker_valid(ticker.upper()):
                self.ticker = ticker.upper()
                self.stop = True
            else:
                utils.print_error(f'Invalid ticker specifed: {ticker}')
        elif update:
            if store.is_ticker_valid(update.upper()):
                self.ticker = update.upper()
                self.stop = True
            else:
                utils.print_error(f'Invalid ticker specifed: {update}')

        self.exchanges = []
        self.indexes = []
        self.task = None
        self.exchanges = [e['abbreviation'] for e in d.EXCHANGES]
        self.indexes = [i['abbreviation'] for i in d.INDEXES]
        self.manager = manager.Manager()

        if ticker:
            self.main_menu(selection=2)
        elif update:
            self.main_menu(selection=5)
        else:
            self.main_menu()

    def main_menu(self, selection=0):
        if not self.stop:
            self.show_database_information()

        menu_items = {
            '1': 'Database Information',
            '2': 'Symbol Information',
            '3': 'Populate Exchange',
            '4': 'Refresh Exchange',
            '5': 'Update Pricing',
            '6': 'Populate Index',
            '7': 'Reset Database',
            '0': 'Exit'
        }

        while True:
            if not self.ticker:
                selection = utils.menu(menu_items, 'Select Operation', 0, 7)

            if selection == 1:
                self.show_database_information()
            elif selection == 2:
                self.show_symbol_information(self.ticker)
            elif selection == 3:
                self.populate_exchange()
            elif selection == 4:
                self.refresh_exchange()
            elif selection == 5:
                self.update_pricing(self.ticker)
            elif selection == 6:
                self.populate_index()
            elif selection == 7:
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

        # utils.print_message('Missing Symbols')
        # exchanges = store.get_exchanges()
        # for e in exchanges:
        #     count = len(self.manager.identify_missing_securities(e))
        #     print(f'{e:>16}:\t{count}')

    def show_symbol_information(self, ticker:str =''):
        if not ticker:
            ticker = utils.input_text('Enter ticker: ')

        if ticker:
            ticker = ticker.upper()
            if store.is_ticker_valid(ticker):
                company = store.get_company(ticker)
                if company is not None:
                    utils.print_message(f'{ticker} Company Information')
                    print(f'Name:\t\t{company["name"]}')
                    print(f'Exchange:\t{company["exchange"]}')
                    print(f'Market Cap:\t{company["marketcap"]}')
                    print(f'Beta:\t\t{company["beta"]:.2f}')
                    print(f'Rating:\t\t{company["rating"]:.2f}')
                    print(f'Indexes:\t{company["indexes"]}')
                    print(f'Sector:\t\t{company["sector"]}')
                    print(f'Industry:\t{company["industry"]}')
                    print(f'URL:\t\t{company["url"]}')
                    print(f'Price Records:\t{company["precords"]}')
                else:
                    utils.print_error(f'{ticker} has no company information')

                history = store.get_history(ticker, 0)
                if not history.empty:
                    print(f'Latest Record:\t{history["date"]:%Y-%m-%d}, closed at ${history["close"]:.2f}')

                utils.print_message(f'{ticker} Recent Price History')
                history = store.get_history(ticker, 10)
                if not history.empty:
                    history.set_index('date', inplace=True)
                    print(history.round(2))

            else:
                utils.print_error(f'{ticker} not found')

    def populate_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.EXCHANGES))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.populate_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_total} {exc} '\
                    f'Symbols populated in {self.manager.task_time:.2f} seconds with {len(self.manager.invalid_tickers)} invalid symbols')

            for i, result in enumerate(self.manager.task_results):
                utils.print_message(f'{i+1:>2}: {result}')

    def refresh_exchange(self, progressbar=True):
        menu_items = {}
        for i, e in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{e}'
        menu_items['0'] = 'Cancel'

        exchange = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if exchange > 0:
            exc = self.exchanges[exchange-1]
            self.task = threading.Thread(target=self.manager.refresh_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            print()
            utils.print_message(f'Identified {self.manager.task_total} missing items. {self.manager.task_success} items filled')

    def update_pricing(self, ticker:str ='', progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items[f'{i+2}'] = 'All'
        menu_items[f'{i+3}'] = 'Ticker'
        menu_items['0'] = 'Cancel'

        if not ticker:
            select = utils.menu(menu_items, 'Select table, or 0 to cancel: ', 0, len(d.EXCHANGES)+2)
        else:
            select = 5

        if select == 5:
            if not ticker:
                ticker = input('Please enter symbol, or 0 to cancel: ').upper()

            if ticker != '0':
                valid = store.is_ticker_valid(ticker)
                if not valid:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
                else:
                    days = self.manager.update_pricing_ticker(ticker)
                    utils.print_message(f'Added {days} days pricing for {ticker}')
                    self.show_symbol_information(ticker=ticker)
        elif select > 0:
            exc = self.exchanges[select-1] if select <= len(d.EXCHANGES) else ''
            self.task = threading.Thread(target=self.manager.update_pricing_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_total} {exc} '\
                    f'Ticker pricing refreshed in {self.manager.task_time:.2f} seconds')

            for i, result in enumerate(self.manager.task_results):
                utils.print_message(f'{i+1:>2}: {result}')

    def delete_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.delete_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('', '', infinite=True)

            self.create_missing_tables()

            if self.manager.task_error == 'Done':
                utils.print_message(f'Deleted exchange {exc} in {self.manager.task_time:.2f} seconds')

    def populate_index(self, progressbar=True):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            self.task = threading.Thread(target=self.manager.populate_index, args=[self.indexes[select-1]])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.task_error == 'Done':
                utils.print_message(f'{self.manager.task_total} {index} Symbols populated in {self.manager.task_time:.2f} seconds')
            else:
                utils.print_error(self.manager.task_error)

    def delete_index(self):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            ind = self.indexes[select-1]
            self.manager.delete_index(ind)

    def create_missing_tables(self):
        self.manager.create_exchanges()
        self.manager.create_indexes()

    def reset_database(self):
        select = utils.input_integer('Are you sure? 1 to reset or 0 to cancel: ', 0, 1)
        if select == 1:
            self.manager.delete_database()
            self.manager.create_database()
            self.manager.create_exchanges()
            self.manager.create_indexes()
            utils.print_message(f'Reset the database')
        else:
            utils.print_message('Database not reset')

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
                    utils.progress_bar(completed, total, prefix=prefix, suffix='Calculating...', length=50)

            utils.print_message('Processed Messages')
            results = [future.result() for future in self.manager.task_futures if future.result() is not None]
            if len(results) > 0:
                [print(result) for result in results]
            else:
                print('None')
        else:
            utils.print_message(f'{self.manager.task_error}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database Management')
    parser.add_argument('-t', '--ticker', help='Get ticker information', required=False)
    parser.add_argument('-u', '--update', help='Update ticker pricing', required=False)

    command = vars(parser.parse_args())

    if command['ticker']:
        Interface(ticker=command['ticker'])
    elif command['update']:
        Interface(update=command['update'])
    else:
        Interface()

