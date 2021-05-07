import os, json
import logging
import time
import threading

import data as d
from data import store as store
from data import manager as manager
from utils import utils as utils

logger = utils.get_logger(logging.ERROR)


class Interface:
    def __init__(self, list='', script=''):
        self.list = list.upper()
        self.exchanges = []
        self.indexes = []
        self.task = None

        self.manager = manager.Manager()
        for e in d.EXCHANGES:
            self.exchanges += [e['abbreviation']]

        for i in d.INDEXES:
            self.indexes += [i['abbreviation']]

        if script:
            if os.path.exists(script):
                try:
                    with open(script) as file_:
                        data = json.load(file_)
                        print(data)
                except Exception as e:
                    utils.print_error('File read error')
            else:
                utils.print_error(f'File "{script}" not found')
        elif not list:
            self.main_menu()
        elif manager.Manager.is_exchange(list):
            self.main_menu()
        elif manager.Manager.is_index(list):
            self.main_menu()
        else:
            utils.print_error('Invalid list specified')

    def main_menu(self):
        self.show_database_information()

        menu_items = {
            '1': 'Database Information',
            '2': 'Symbol Information',
            '3': 'Populate Exchange',
            '4': 'Refresh Exchange',
            '5': 'Update Pricing',
            '6': 'Populate Index',
            '7': 'Create Missing Exchanges and Indexes',
            '8': 'Reset Database',
            '0': 'Exit'
        }

        while True:
            selection = utils.menu(menu_items, 'Select Operation', 0, 8)

            if selection == 1:
                self.show_database_information(all=True)
            elif selection == 2:
                self.show_symbol_information()
            elif selection == 3:
                self.populate_exchange()
            elif selection == 4:
                self.refresh_exchange()
            elif selection == 5:
                self.update_pricing()
            elif selection == 6:
                self.populate_index()
            elif selection == 7:
                self.create_missing_tables()
            elif selection == 8:
                self.reset_database()
            elif selection == 0:
                break

    def show_database_information(self, all=False):
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

        if all:
            utils.print_message('Missing Symbols')
            exchanges = store.get_exchanges()
            for e in exchanges:
                count = len(self.manager.identify_missing_securities(e))
                print(f'{e:>16}:\t{count}')

            utils.print_message('Inactive Symbols')
            exchanges = store.get_exchanges()
            for e in exchanges:
                count = len(self.manager.identify_inactive_securities(e))
                print(f'{e:>16}:\t{count}')

            utils.print_message('Missing Information')
            exchanges = store.get_exchanges()
            for e in exchanges:
                count = len(self.manager.identify_incomplete_securities_companies(e))
                print(f'{e:>16}:\t{count} missing company')

            for e in exchanges:
                count = len(self.manager.identify_incomplete_securities_price(e))
                print(f'{e:>16}:\t{count} missing price')

            utils.print_message('Master Exchange Symbol List')
            for exchange in d.EXCHANGES:
                exc = list(store.get_exchange_symbols_master(exchange['abbreviation']))
                count = len(exc)
                print(f'{exchange["abbreviation"]:>16}:\t{count} symbols')

            utils.print_message('Master Exchange Common Symbols')
            nasdaq_nyse, nasdaq_amex, nyse_amex = self.manager.identify_common_securities()
            count = len(nasdaq_nyse)
            name = 'NASDAQ-NYSE'
            print(f'{name:>16}:\t{count} symbols')
            count = len(nasdaq_amex)
            name = 'NASDAQ-AMEX'
            print(f'{name:>16}:\t{count} symbols')
            count = len(nyse_amex)
            name = 'NYSE-AMEX'
            print(f'{name:>16}:\t{count} symbols')

    def show_symbol_information(self):
        symbol = utils.input_text('Enter symbol: ')
        if symbol:
            symbol = symbol[:4].upper()
            if store.is_symbol_valid(symbol):
                company = store.get_company(symbol)
                if company is not None:
                    utils.print_message(f'{symbol} Company Information')
                    print(f'Name:\t\t{company["name"]}')
                    print(f'Sector:\t\t{company["sector"]}')
                    print(f'Industry:\t{company["industry"]}')
                    print(f'Indexes:\t{company["indexes"]}')
                    print(f'URL:\t\t{company["url"]}')
                    print(f'Price Records:\t{company["precords"]}')
                else:
                    utils.print_error(f'{symbol} has no company information')

                history = store.get_history(symbol, 0)
                if not history.empty:
                    print(f'Latest Record:\t{history["date"]:%Y-%m-%d}, closed at ${history["close"]:.2f}')

                utils.print_message(f'{symbol} Recent Price History')
                history = store.get_history(symbol, 10)
                history.set_index('date', inplace=True)
                if not history.empty:
                    print(history)

            else:
                utils.print_error(f'{symbol} not found')

    def populate_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.populate_exchange, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.items_error == 'Done':
                utils.print_message(f'{self.manager.items_total} {exc} '\
                    f'Symbols populated in {self.manager.items_time:.2f} seconds with {len(self.manager.invalid_symbols)} invalid symbols')

            for i, result in enumerate(self.manager.items_results):
                utils.print_message(f'{i+1:>2}: {result}', creturn=False)

    def refresh_exchange(self, progressbar=True):
        menu_items = {
            '1': 'Missing Company Information',
            '2': 'Missing Price Information',
            '0': 'Cancel',
        }
        area = utils.menu(menu_items, 'Select item to refresh, or 0 to cancel: ', 0, 2)

        if area > 0:
            areaname = ['companies', 'pricing']
            menu_items = {}
            for i, e in enumerate(self.exchanges):
                menu_items[f'{i+1}'] = f'{e}'
            menu_items['0'] = 'Cancel'

            exchange = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
            if exchange > 0:
                exc = self.exchanges[exchange-1]
                self.task = threading.Thread(target=self.manager.refresh_exchange, args=[exc, areaname[area-1]])
                self.task.start()

                if progressbar:
                    print()
                    self._show_progress('Progress', 'Completed')

                print()
                utils.print_message(f'Completed {exc} {areaname[area-1]} refresh in {self.manager.items_time:.2f} seconds', creturn=2)
                utils.print_message(f'Identified {self.manager.items_total} missing items. {self.manager.items_success} items filled', creturn=0)

    def update_pricing(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items[f'{i+2}'] = 'All'
        menu_items['0'] = 'Cancel'

        select = utils.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.EXCHANGES)+1)
        if select > 0:
            exc = self.exchanges[select-1] if select <= len(d.EXCHANGES) else ''
            self.task = threading.Thread(target=self.manager.update_pricing, args=[exc])
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', 'Completed')

            if self.manager.items_error == 'Done':
                utils.print_message(f'{self.manager.items_total} {exc} '\
                    f'Ticker pricing refreshed in {self.manager.items_time:.2f} seconds')

            for i, result in enumerate(self.manager.items_results):
                utils.print_message(f'{i+1:>2}: {result}', creturn=False)

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

            if self.manager.items_error == 'Done':
                utils.print_message(f'Deleted exchange {exc} in {self.manager.items_time:.2f} seconds')

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

            if self.manager.items_error == 'Done':
                utils.print_message(f'{self.manager.items_total} {index} Symbols populated in {self.manager.items_time:.2f} seconds')
            else:
                utils.print_error(self.manager.items_error)

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
            self.manager.create_exchanges()
            self.manager.create_indexes()
            utils.print_message(f'Reset the database')
        else:
            utils.print_message('Database not reset')

    def list_invalid(self):
        utils.print_message(f'Invalid: {self.manager.invalid_symbols}')

    def _show_progress(self, prefix, suffix):
        while not self.manager.items_error: pass

        if self.manager.items_error == 'None':
            utils.progress_bar(self.manager.items_completed, self.manager.items_total, prefix=prefix, suffix=suffix, length=50, reset=True)
            while self.task.is_alive and self.manager.items_error == 'None':
                time.sleep(0.20)
                total = self.manager.items_total
                completed = self.manager.items_completed
                success = self.manager.items_success
                symbol = self.manager.items_symbol
                tasks = len([True for future in self.manager.items_futures if future.running()])

                if total > 0:
                    utils.progress_bar(completed, total, prefix=prefix, suffix=suffix, symbol=symbol, length=50, success=success, tasks=tasks)
                else:
                    utils.progress_bar(completed, total, prefix=prefix, suffix='Calculating...', length=50)
            print()
            [print(future.result()) for future in self.manager.items_futures]
        else:
            utils.print_message(f'{self.manager.items_error}')


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Data Management')
    subparser = parser.add_subparsers(help='Specify the desired command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Load a list')
    parser_a.add_argument('-l', '--list', help='Specify the list', required=False, default='TEST')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='scripts/script.json')

    command = vars(parser.parse_args())

    if 'script' in command.keys():
        Interface(script=command['script'])
    elif 'list' in command.keys():
        Interface(command['list'])
    else:
        Interface()
