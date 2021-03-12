import sys, os, json, time, threading
import logging
import datetime

from pricing.fetcher import validate_ticker
from screener.screener import Screener, VALID_SCREENS
from utils import utils as u


logger = u.get_logger(logging.WARNING)


class Interface:
    def __init__(self, table_name, script=None):
        self.table_name = table_name
        self.screener = Screener(self.table_name)
        self.screen_name = ''
        self.screens = []
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
                '2': f'Select Screen ({self.screen_name})',
                '3': 'Run Screen',
                '4': 'Show Results',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 4)

            if selection == 1:
                self.select_table()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                self.run_screen()
            elif selection == 4:
                self.print_identified()
            elif selection == 0:
                break

    def select_table(self):
        loop = True
        while loop:
            table = input('Please enter valid table name, or 0 to cancel: ').upper()
            if table == '0':
                loop = False
            else:
                self.screener = Screener(table)
                if self.screener.valid():
                    self.table_name = table
                    loop = False
                else:
                    u.print_error('Invalid table name. Try again or select "0" to cancel')

    def select_screen(self):
        self.screens = []
        basepath = '.'
        with os.scandir(basepath) as entries:
            for entry in entries:
                if entry.is_file():
                    if '.screen' in entry.name:
                        head, sep, tail = entry.name.partition('.')
                        self.screens += [head]

        if len(self.screens) > 0:
            self.screens.sort()
            menu_items = {}
            for index, item in enumerate(self.screens):
                menu_items[f'{index+1}'] = f'{item}'

            menu_items['0'] = 'Cancel'
            selection = u.menu(menu_items, 'Select Screen', 0, index+1)
            if selection > 0:
                self.screen_name = self.screens[selection-1]
        else:
            u.print_message('No screen files found')

    def run_screen(self):
        if self.screener.valid():
            menu_items = {
                '1': f'{VALID_SCREENS[0].title()}',
                '2': f'{VALID_SCREENS[1].title()}',
                '0': 'Cancel',
            }

            while True:
                selection = u.menu(menu_items, 'Select Screen', 0, 2)

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
