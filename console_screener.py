import os
import json
import time
import threading
import logging

from screener.screener import Screener
from data import history as h
from fetcher import fetcher as f
from utils import utils as u


logger = u.get_logger(logging.WARNING)

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = '.screen'

class Interface:
    def __init__(self, table='', screen='', script=''):
        self.table_name = table.upper()
        self.screen_name = screen
        self.script = []
        self.results = []
        self.valids = 0
        self.screener = None
        self.time = 0.0

        # Initialize data fetcher
        f.initialize()

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
        else:
            if self.table_name:
                try:
                    self.screener = Screener(self.table_name)
                    self._open_table(True)
                    if not self.screener.valid():
                        self.table_name = ''
                        self.screener = None
                except ValueError as e:
                    self.screener = None
                    self.table_name = ''
                    u.print_error(f'Table "{self.table_name}" not found')

            if self.screen_name:
                if os.path.exists(BASEPATH+screen+SCREEN_SUFFIX):
                    self.screen_name = BASEPATH + self.screen_name + SCREEN_SUFFIX
                    if not self.screener.load_script(self.screen_name):
                        self.screen_name = ''
                        u.print_error('Invalid screen script')
                else:
                    self.screen_name = ''
                    u.print_error(f'File "{self.screen_name}" not found')

            self.main_menu()


    def main_menu(self):
        if self.screener is None:
            self.screener = Screener()

        while True:
            menu_items = {
                '1': 'Select Table',
                '2': 'Select Script',
                '3': 'Run Script',
                '4': 'Show Results',
                '0': 'Exit'
            }

            if self.table_name:
                menu_items['1'] = f'Select Table ({self.table_name}, {len(self.screener.symbols)} Symbols)'

            if self.screen_name:
                filename = os.path.basename(self.screen_name)
                head, sep, tail = filename.partition('.')
                menu_items['2'] = f'Select Script ({head})'

            if len(self.results) > 0:
                menu_items['4'] = f'Show Results ({self.valids})'

            selection = u.menu(menu_items, 'Select Operation', 0, 4)

            if selection == 1:
                self.select_table(True)
            elif selection == 2:
                self.select_script()
            elif selection == 3:
                self.run_script(True)
            elif selection == 4:
                self.print_results()
            elif selection == 0:
                break

    def select_table(self, progressbar):
        menu_items = {}
        for index, item in enumerate(h.VALID_LISTS):
            menu_items[f'{index+1}'] = f'{item}'
        menu_items['0'] = 'Cancel'

        selection = u.menu(menu_items, 'Select Table', 0, len(h.VALID_LISTS))
        if selection > 0:
            self.screener = Screener(h.VALID_LISTS[selection-1], script_name=self.screen_name)

            self._open_table(progressbar)

            if self.screener.valid():
                self.table_name = h.VALID_LISTS[selection-1]

    def select_script(self):
        self.script = []
        self.results = []
        self.valids = 0
        paths = []
        with os.scandir(BASEPATH) as entries:
            for entry in entries:
                if entry.is_file():
                    if '.screen' in entry.name:
                        self.script += [entry.path]
                        head, sep, tail = entry.name.partition('.')
                        paths += [head.title()]

        if len(self.script) > 0:
            self.script.sort()
            paths.sort()

            menu_items = {}
            for index, item in enumerate(paths):
                menu_items[f'{index+1}'] = f'{item}'
            menu_items['0'] = 'Cancel'

            selection = u.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen_name = self.script[selection-1]
                self.results = []

                if not self.screener.load_script(self.screen_name):
                    u.print_error('Error in script file')

        else:
            u.print_message('No script files found')

    def run_script(self, progressbar):
        if not self.table_name:
            u.print_error('No table specified', True)
        elif not self.screen_name:
            u.print_error('No script specified', True)
        elif self.screener.load_script(self.screen_name):
            self.results = []
            self.valids = 0
            task = threading.Thread(target=self.screener.run_script)
            task.start()
            tic = time.perf_counter()

            if progressbar:
                self._show_progress('Progress', 'Completed', 1)

            # Wait for thread to finish
            while task.is_alive(): pass

            toc = time.perf_counter()
            self.time = toc - tic

            if self.screener.error == 'None':
                self.results = self.screener.results
                for result in self.results:
                    if result:
                        self.valids += 1

                u.print_message(f'{self.valids} Symbols Identified in {self.time:.2f} seconds', True)
            else:
                self.results = []
                self.valids = 0
                u.print_error(self.screener.error, True)
        else:
            u.print_error('Script error', True)

    def print_results(self, all=False):
        if not self.table_name:
            u.print_error('No table specified', True)
        elif not self.screen_name:
            u.print_error('No script specified', True)
        elif len(self.results) == 0:
            u.print_message('No symbols were located', True)
        else:
            u.print_message('Symbols Identified', True)
            index = 0
            for result in self.results:
                if all:
                    index += 1
                    print(f'{result} ({sum(result.values)})')
                    if (index) % 10 == 0:
                        print()
                elif result:
                    index += 1
                    print(f'{result} ', end='')
                    if (index) % 10 == 0:
                        print()

        print()

    def _open_table(self, progressbar):
        task = threading.Thread(target=self.screener.open)
        task.start()

        if progressbar:
            self._show_progress('Progress', 'Symbols loaded', 2)

        # Wait for thread to finish
        while task.is_alive(): pass

    def _show_progress(self, prefix, suffix, scheme):
        # Wait for either an error or running to start, or not, the progress bar
        while not self.screener.error: pass

        if self.screener.error == 'None':
            total = self.screener.items_total
            completed = self.screener.items_completed
            u.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
            while completed < total:
                time.sleep(0.25)
                if scheme == 1:
                    sfx = suffix + f' - {self.screener.active_symbol} ({self.screener.matches})' + '    '
                elif scheme == 2:
                    sfx = suffix
                completed = self.screener.items_completed
                u.progress_bar(completed, total, prefix=prefix, suffix=sfx, length=50)


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Screener')
    subparser = parser.add_subparsers(help='Specify the desired command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Load a symbol table')
    parser_a.add_argument('-t', '--table', help='Specify a symbol table', required=False, default='')
    parser_a.add_argument('-s', '--screen', help='Specify a screening script', required=False, default='')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='scripts/script.json')

    command = vars(parser.parse_args())

    if 'script' in command.keys():
        Interface('TEST', script=command['script'])
    else:
        table = ''
        if 'table' in command.keys():
            table = command['table']

        if 'screen' in command.keys():
            Interface(table, command['screen'])
        else:
            Interface(table)
