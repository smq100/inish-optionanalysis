import os
import json
import time
import threading
import logging

from screener.screener import Screener
import data as d
from data import store as o
from utils import utils as utils

logger = utils.get_logger(logging.ERROR)

BASEPATH = os.getcwd()+'/screener/screens/'
SCREEN_SUFFIX = '.screen'


class Interface:
    def __init__(self, table='', screen='', script='', live=False):
        self.table = table.upper()
        self.screen = screen
        self.script = []
        self.live = live
        self.results = []
        self.valids = 0
        self.screener = None
        self.type = ''

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
        else:
            if self.table:
                if o.is_exchange(self.table):
                    self.type = 'exchange'
                elif o.is_index(self.table):
                    self.type = 'index'
                else:
                    raise ValueError(f'Table not found: {table}')

                self.screener = Screener(table=self.table, live=self.live)

            if self.screen:
                if os.path.exists(BASEPATH+screen+SCREEN_SUFFIX):
                    self.screen = BASEPATH + self.screen + SCREEN_SUFFIX
                    if not self.screener.load_script(self.screen):
                        self.screen = ''
                        utils.print_error('Invalid screen script')
                else:
                    utils.print_error(f'File "{self.screen}" not found')
                    self.screen = ''

            self.main_menu()

    def main_menu(self):
        while True:
            source = 'live' if self.live else d.ACTIVE_DB
            menu_items = {
                '1': f'Select Data Source ({source})',
                '2': 'Select Exchange',
                '3': 'Select Index',
                '4': 'Select Script',
                '5': 'Run Script',
                '6': 'Show Results',
                '0': 'Exit'
            }

            if self.table:
                if self.type == 'exchange':
                    menu_items['2'] = f'Select Exchange ({self.table}, {len(self.screener.symbols)} Symbols)'
                else:
                    menu_items['3'] = f'Select Index ({self.table}, {len(self.screener.symbols)} Symbols)'

            if self.screen:
                filename = os.path.basename(self.screen)
                head, sep, tail = filename.partition('.')
                menu_items['4'] = f'Select Script ({head})'

            if len(self.results) > 0:
                menu_items['6'] = f'Show Results ({self.valids})'

            selection = utils.menu(menu_items, 'Select Operation', 0, 6)

            if selection == 1:
                self.select_source()
            if selection == 2:
                self.select_exchange()
            if selection == 3:
                self.select_index()
            elif selection == 4:
                self.select_script()
            elif selection == 5:
                self.run_script(True)
            elif selection == 6:
                self.print_results()
            elif selection == 0:
                break

    def select_source(self):
        menu_items = {
            '1': 'Database',
            '2': 'Live',
            '0': 'Cancel',
        }

        selection = utils.menu(menu_items, 'Select Data Source', 0, 2)
        if selection == 1:
            self.live = False
        elif selection == 2:
            self.live = True

        if self.table:
            self.screener = Screener(table=self.table, script=self.screen, live=self.live)

    def select_exchange(self):
        menu_items = {}
        for exchange, item in enumerate(d.EXCHANGES):
            menu_items[f'{exchange+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Exchange', 0, len(d.EXCHANGES))
        if selection > 0:
            exc = d.EXCHANGES[selection-1]['abbreviation']
            if len(o.get_exchange_symbols(exc)) > 0:
                self.screener = Screener(exc, script=self.screen, live=self.live)
                if self.screener.valid():
                    self.table = exc
                    self.type = 'exchange'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Exchange {exc} has no symbols')

    def select_index(self):
        menu_items = {}
        for index, item in enumerate(d.INDEXES):
            menu_items[f'{index+1}'] = f'{item["abbreviation"]}'
        menu_items['0'] = 'Cancel'

        selection = utils.menu(menu_items, 'Select Index', 0, len(d.INDEXES))
        if selection > 0:
            index = d.INDEXES[selection-1]['abbreviation']
            if len(o.get_index_symbols(index)) > 0:
                self.screener = Screener(index, script=self.screen, live=self.live)
                if self.screener.valid():
                    self.table = index
                    self.type = 'index'
            else:
                self.table = ''
                self.screener = None
                utils.print_error(f'Index {index} has no symbols')

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

            selection = utils.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen = self.script[selection-1]
                self.results = []

                if self.screener is not None:
                    if not self.screener.load_script(self.screen):
                        utils.print_error('Error in script file')

        else:
            utils.print_message('No script files found')

    def run_script(self, progressbar):
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen:
            utils.print_error('No script specified')
        elif self.screener.load_script(self.screen):
            self.results = []
            self.valids = 0
            task = threading.Thread(target=self.screener.run_script)
            task.start()

            if progressbar:
                self._show_progress('Progress', 'Completed')

            # Wait for thread to finish
            while task.is_alive(): pass

            if self.screener.items_error == 'None':
                self.results = self.screener.results
                for result in self.results:
                    if result:
                        self.valids += 1

                utils.print_message(f'{self.valids} Symbols Identified in {self.screener.items_time:.2f} seconds')

                for i, result in enumerate(self.screener.items_results):
                    utils.print_message(f'{i+1:>2}: {result}', creturn=False)
            else:
                self.results = []
                self.valids = 0
                utils.print_error(self.screener.items_error)
        else:
            utils.print_error('Script error')

    def print_results(self, all=False):
        if not self.table:
            utils.print_error('No table specified')
        elif not self.screen:
            utils.print_error('No script specified')
        elif len(self.results) == 0:
            utils.print_message('No symbols were located')
        else:
            utils.print_message('Symbols Identified')
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

    def _show_progress(self, prefix, suffix):
        # Wait for either an error or running to start, or not, the progress bar
        while not self.screener.items_error: pass

        if self.screener.items_error == 'None':
            total = self.screener.items_total
            completed = self.screener.items_completed

            utils.progress_bar(completed, total, prefix=prefix, suffix=suffix, length=50)
            while completed < total:
                time.sleep(0.25)
                completed = self.screener.items_completed
                success = self.screener.items_success
                symbol = self.screener.items_symbol
                utils.progress_bar(completed, total, prefix=prefix, suffix=suffix, symbol=symbol, length=50, success=success)
            print()


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
        screen = ''

        if 'table' in command.keys():
            table = command['table']

        if 'screen' in command.keys():
            screen = command['screen']

        Interface(table, screen)
