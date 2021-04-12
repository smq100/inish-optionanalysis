import os, json
import logging
import time
import threading

from data import manager as m
from utils import utils as u

logger = u.get_logger(logging.WARNING)


class Interface:
    def __init__(self, list='', script=''):
        self.list = list.upper()
        self.exchanges = []
        self.indexes = []

        self.manager = m.Manager()
        for e in m.EXCHANGES:
            self.exchanges += [e['abbreviation']]

        for i in m.INDEXES:
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
            '2': 'Database information',
            '3': 'Populate Exchanges',
            '4': 'Populate Indexes',
            '5': 'List invalid symbols',
            '0': 'Exit'
        }

        while True:
            selection = u.menu(menu_items, 'Select Operation', 0, 5)

            if selection == 1:
                self.reset()
            elif selection == 2:
                self.show_information()
            elif selection == 3:
                self.populate_exchange()
            elif selection == 4:
                self.populate_index()
            elif selection == 5:
                self.list_invalid()
            elif selection == 0:
                break

    def reset(self):
        self.manager.delete_database(recreate=True)
        self.manager.build_exchanges()
        self.manager.build_indexes()
        u.print_message(f'Reset database "{m.SQLITE_DATABASE_PATH}"')

    def show_information(self):
        u.print_message(f'Information for database "./{m.SQLITE_DATABASE_PATH}"', True)
        info = self.manager.get_database_info()
        for i in info:
            print(f'{i["table"].title():>9}:\t{i["count"]} records')

        u.print_message('Exchange Information', True)
        info = self.manager.get_exchange_info()
        for i in info:
            print(f'{i["exchange"]:>9}:\t{i["count"]} symbols')

    def populate_exchange(self, progressbar=True):
        print('\nSelect Exchange')
        print('-------------------------')
        for i, exchange in enumerate(self.exchanges):
            print(f'{i+1})\t{exchange}')

        select = u.input_integer('Select exchange, or 0 to cancel: ', 0, i+1)
        if select > 0:
            task = threading.Thread(target=self.manager.populate_exchange, args=[self.exchanges[select-1]])
            task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while task.is_alive(): pass

            toc = time.perf_counter()
            totaltime = toc - tic

            if self.manager.error == 'None':
                u.print_message(f'{self.manager.items_total} {exchange} \
                    Symbols populated in {totaltime:.2f} seconds with {len(self.manager.invalid_companies)} invalid symbols', True)

    def populate_index(self, progressbar=True):
        print('\nSelect Index')
        print('-------------------------')
        for i, index in enumerate(self.indexes):
            print(f'{i+1})\t{index}')

        select = u.input_integer('Select index, or 0 to cancel: ', 0, i+1)
        if select > 0:
            task = threading.Thread(target=self.manager.populate_index, args=[self.indexes[select-1]])
            task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while task.is_alive(): pass

            toc = time.perf_counter()
            totaltime = toc - tic

            if self.manager.error == 'None':
                u.print_message(f'{self.manager.items_total} {index} Symbols populated in {totaltime:.2f} seconds', True)

    def list_invalid(self):
        u.print_message(f'Invalid: {self.manager.invalid_companies}', True)

    def _show_progress(self, prefix, suffix, scheme):
        while not self.manager.error: pass

        if self.manager.error == 'None':
            total = self.manager.items_total
            completed = self.manager.items_completed

            u.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
            while completed < total:
                time.sleep(0.25)
                completed = self.manager.items_completed
                u.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
        else:
            u.print_message(f'{self.manager.error}', True)

if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Scoring')
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
