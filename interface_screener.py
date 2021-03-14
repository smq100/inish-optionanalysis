import sys, os, json, time, threading
import logging
import datetime

from pricing.fetcher import validate_ticker
from screener.screener import Screener, VALID_LISTS
from utils import utils as u


logger = u.get_logger(logging.DEBUG)


class Interface:
    def __init__(self, table_name, script=None):
        self.table_name = table_name
        self.screener = Screener(self.table_name)
        self.script_name = ''
        self.script = []
        self.results = []

        if self.screener is not None:
            if script is not None:
                if os.path.exists(script):
                    try:
                        with open(script) as file_:
                            data = json.load(file_)
                            print(data)
                    except:
                        u.print_error('File read error')
                else:
                    u.print_error(f'File "{script}" not found')
            else:
                self.main_menu()
        else:
            u.print_error('Invalid table specified')

    def main_menu(self):
        while True:

            menu_items = {
                '1': f'Select Table ({self.table_name}, {len(self.screener.symbols)} Symbols)',
                '2': 'Select Script',
                '3': 'Run Script',
                '4': 'Show Results',
                '0': 'Exit'
            }

            if self.script_name:
                filename = os.path.basename(self.script_name)
                head, sep, tail = filename.partition('.')
                menu_items['3'] = f'Run Script ({head})'

            selection = u.menu(menu_items, 'Select Operation', 0, 4)

            if selection == 1:
                self.select_table()
            elif selection == 2:
                self.select_script()
            elif selection == 3:
                self.run_script()
            elif selection == 4:
                self.print_identified()
            elif selection == 0:
                break

    def select_table(self):
        menu_items = {}
        for index, item in enumerate(VALID_LISTS):
            menu_items[f'{index+1}'] = f'{item}'
        menu_items['0'] = 'Cancel'

        selection = u.menu(menu_items, 'Select Table', 0, len(VALID_LISTS))
        if selection > 0:
            self.screener = Screener(VALID_LISTS[selection-1])
            if self.screener.valid():
                self.table_name = VALID_LISTS[selection-1]

    def select_script(self):
        self.script = []
        paths = []
        basepath = os.getcwd()+'/screener/scripts'
        with os.scandir(basepath) as entries:
            for entry in entries:
                if entry.is_file():
                    if '.script' in entry.name:
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

            selection = u.menu(menu_items, 'Select Script', 0, index+1)
            if selection > 0:
                self.script_name = self.script[selection-1]

                if not self.screener.load_script(self.script_name):
                    u.print_error('Error in script file')

        else:
            u.print_message('No script files found')

    def run_script(self):
        try:
            self.screener.run_script()
        except Exception as e:
            u.print_error(f'Error running script: {str(e)}')

    def run_screen(self):
        if self.screener.valid():
            menu_items = {}
            for index, item in enumerate(VALID_SCREENS):
                menu_items[f'{index+1}'] = f'{item.title()}'
            menu_items['0'] = 'Cancel'

            while True:
                selection = u.menu(menu_items, 'Select Screen', 0, len(VALID_SCREENS))

                if selection == 1:
                    task = threading.Thread(target=self.screener.run_screen, args=(menu_items['1'],))
                    task.start()

                    self._show_progress()

                    # Wait for thread to finish
                    while task.is_alive(): pass

                    self.results = self.screener.results
                    u.print_message(f'{len(self.results)} Symbols Identified', True)
                    break

                if selection == 2:
                    self.results = self.screener.run_screen(menu_items['2'])
                    u.print_message(f'{len(self.results)} Symbols Identified', True)
                    break

                if selection == 0:
                    break
        else:
            u.print_error('No table selected')

    def print_identified(self):
        if len(self.results) > 0:
            u.print_message('Symbols Identified', True)
            for index, symbol in enumerate(self.results):
                print(f'{index:3n}: {symbol}')
        else:
            u.print_message('No symbols were located', True)

    def _show_progress(self):
        total = self.screener.items_total
        completed = self.screener.items_completed

        u.progress_bar(completed, total, prefix='Progress:', suffix='Completed', length=50)
        while completed < total:
            time.sleep(0.1)
            completed = self.screener.items_completed
            u.progress_bar(completed, total, prefix='Progress:', suffix='Completed', length=50)


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Scoring')
    subparser = parser.add_subparsers(help='Specify the desired command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Load a symbol table')
    parser_a.add_argument('-t', '--table', help='Specify the symbol table', required=False, default='SP500')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'script' in command.keys():
        Interface('TEST', script=command['script'])
    elif 'table' in command.keys():
        Interface(command['table'])
    else:
        Interface('TEST')