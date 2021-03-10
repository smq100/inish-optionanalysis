import sys, os, json
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
        self.symbols = None
        self.located = []

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
                '1': f'Select Table ({self.table_name})',
                '2': 'Run Screen',
                '3': 'Fetch Symbols',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 3)

            if selection == 1:
                self.select_table()
            elif selection == 2:
                self.select_screen()
            elif selection == 3:
                self.fetch_symbols()
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
        if self.screener.valid():
            menu_items = {
                '1': f'{VALID_SCREENS[0].title()}',
                '0': 'Cancel',
            }

            while True:
                selection = u.menu(menu_items, 'Select Screen', 0, 1)

                if selection == 1:
                    self.located = self.screener.run_screen(menu_items['1'])
                    self.print_located()
                    break

                if selection == 0:
                    break
        else:
            u.print_error('No table selected')

    def fetch_symbols(self):
        self.symbols = self.screener.symbols
        u.print_message(f'{len(self.symbols)} symbols fetched: {self.symbols[:3]} to {self.symbols[-3:]}')

    def print_located(self):
        if len(self.located) > 0:
            u.print_message('Symbols Identified', True)
            for symbol in self.located:
                print(symbol)
        else:
            u.print_error('No symbols were located')


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
        Interface('SP500', script=command['script'])
    elif 'table' in command.keys():
        Interface(command['table'])
    else:
        Interface('SP500')
