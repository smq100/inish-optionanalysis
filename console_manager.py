import os, json
import logging
import time
import threading

import data as d
from data import store as o
from data import manager as m
from utils import utils as u

logger = u.get_logger(logging.WARNING)


class Interface:
    def __init__(self, list='', script=''):
        self.list = list.upper()
        self.exchanges = []
        self.indexes = []
        self.task = None

        self.manager = m.Manager()
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
                    u.print_error('File read error')
            else:
                u.print_error(f'File "{script}" not found')
        elif not list:
            self.main_menu()
        elif m.Manager.is_exchange(list):
            self.main_menu()
        elif m.Manager.is_index(list):
            self.main_menu()
        else:
            u.print_error('Invalid list specified')

    def main_menu(self):
        self.show_information()

        menu_items = {
            '1': 'Reset Database',
            '2': 'Database Information',
            '3': 'Populate Exchange',
            '4': 'Refresh Exchange',
            '5': 'Delete Exchange',
            '6': 'Master Exchange List',
            '7': 'Populate Index',
            '8': 'Delete Index',
            '0': 'Exit'
        }

        while True:
            selection = u.menu(menu_items, 'Select Operation', 0, 8)

            if selection == 1:
                self.reset()
            elif selection == 2:
                self.show_information(brief=False)
            elif selection == 3:
                self.populate_exchange()
            elif selection == 4:
                self.refresh_exchange()
            elif selection == 5:
                self.delete_exchange()
            elif selection == 6:
                self.show_master_list()
            elif selection == 7:
                self.populate_index()
            elif selection == 8:
                self.delete_index()
            elif selection == 0:
                break

    def reset(self):
        select = u.input_integer('Are you sure? 1 to reset or 0 to cancel: ', 0, 1)
        if select == 1:
            self.manager.delete_database(recreate=True)
            self.manager.build_exchanges()
            self.manager.build_indexes()
            u.print_message(f'Reset the database')
        else:
            u.print_message('Database not reset')

    def show_information(self, brief=True):
        u.print_message(f'Database Information ({d.ACTIVE_DB})')
        info = self.manager.get_database_info()
        for i in info:
            print(f'{i["table"].title():>9}:\t{i["count"]} records')

        u.print_message('Exchange Information')
        info = self.manager.get_exchange_info()
        for i in info:
            print(f'{i["exchange"]:>9}:\t{i["count"]} symbols')

        u.print_message('Index Information')
        info = self.manager.get_index_info()
        for i in info:
            print(f'{i["index"]:>9}:\t{i["count"]} symbols')

        if not brief:
            u.print_message('Missing Symbols')
            exchanges = o.get_exchanges()
            for e in exchanges:
                count = len(self.manager.identify_missing_securities(e))
                print(f'{e:>9}:\t{count} symbols')

            self.show_master_list()

    def populate_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = u.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.populate_exchange, args=[exc])
            self.task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while self.task.is_alive(): pass

            toc = time.perf_counter()
            totaltime = toc - tic

            if self.manager.error == 'None':
                u.print_message(f'{self.manager.items_total} {exc} '\
                    f'Symbols populated in {totaltime:.2f} seconds with {len(self.manager.invalid_symbols)} invalid symbols')

    def refresh_exchange(self, progressbar=True):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = u.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            exc = self.exchanges[select-1]

            self.task = threading.Thread(target=self.manager.refresh_exchange, args=[exc])
            self.task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while self.task.is_alive(): pass

            toc = time.perf_counter()
            totaltime = toc - tic

            if self.manager.error == 'None':
                u.print_message(f'{self.manager.items_total} {exc} '\
                    f'Symbols refreshed in {totaltime:.2f} seconds with {len(self.manager.invalid_symbols)} invalid symbols')

    def delete_exchange(self):
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        menu_items['0'] = 'Cancel'

        select = u.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            exc = self.exchanges[select-1]
            self.manager.delete_exchange(exc)

    def show_master_list(self):
        u.print_message('Master Exchange Symbol List')
        for exchange in d.EXCHANGES:
            exc = list(o.get_exchange_symbols_master(exchange['abbreviation']))
            count = len(exc)
            print(f'{exchange["abbreviation"]}:\t{count} symbols')

        u.print_message('Master Exchange Common Symbols')
        nasdaq_nyse, nasdaq_amex, nyse_amex = self.manager.identify_common_securities()
        count = len(nasdaq_nyse)
        print(f'NASDAQ-NYSE:\t{count} symbols')
        count = len(nasdaq_amex)
        print(f'NASDAQ-AMEX:\t{count} symbols')
        count = len(nyse_amex)
        print(f'NYSE-AMEX:\t{count} symbols')

    def populate_index(self, progressbar=True):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = u.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            self.task = threading.Thread(target=self.manager.populate_index, args=[self.indexes[select-1]])
            self.task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while self.task.is_alive(): pass

            toc = time.perf_counter()
            totaltime = toc - tic

            if self.manager.error == 'None':
                u.print_message(f'{self.manager.items_total} {index} Symbols populated in {totaltime:.2f} seconds')

    def delete_index(self):
        menu_items = {}
        for i, index in enumerate(self.indexes):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = u.menu(menu_items, 'Select index, or 0 to cancel: ', 0, len(d.INDEXES))
        if select > 0:
            ind = self.indexes[select-1]
            self.manager.delete_index(ind)

    def list_invalid(self):
        u.print_message(f'Invalid: {self.manager.invalid_symbols}')

    def _show_progress(self, prefix, suffix, scheme):
        while not self.manager.error: pass

        if self.manager.error == 'None':
            total = self.manager.items_total
            completed = self.manager.items_completed

            u.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
            while completed < total and self.task.is_alive and self.manager.error == 'None':
                time.sleep(0.25)
                completed = self.manager.items_completed
                u.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
        else:
            u.print_message(f'{self.manager.error}')

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
