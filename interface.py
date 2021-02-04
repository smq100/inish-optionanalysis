''' TODO '''

import sys, os, json
import datetime

import pandas as pd

from strategy.strategy import Leg
from strategy.call import Call
from strategy.put import Put
from strategy.vertical import Vertical
from utils import utils as u

MAX_ROWS = 50
MAX_COLS = 18

class Interface():
    '''TODO'''

    def __init__(self, ticker, strategy=None, direction=None, script=None):
        pd.options.display.float_format = '{:,.2f}'.format

        ticker = ticker.upper()

        if strategy is not None:
            if self._load_strategy(ticker, strategy, direction):
                self.main_menu()
        elif script is not None:
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
            self.strategy = Call(ticker)
            self.main_menu()


    def main_menu(self):
        '''Displays opening menu'''

        while True:
            menu_items = {
                '1': f'Specify Symbol ({self.strategy.ticker})',
                '2': f'Specify Strategy ({self.strategy})',
                '3': 'Analyze Stategy',
                '4': 'Modify Leg',
                '5': 'Calculate Values',
                '6': 'Plot Leg Values',
                '7': 'Options',
                '8': 'Exit'
            }

            self.write_legs()

            print('\nSelect Option')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.enter_symbol()
            elif selection == '2':
                if self.enter_strategy():
                    self.calculate()
            elif selection == '3':
                self.analyze()
            elif selection == '4':
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = int(input('Enter Leg: ')) - 1
                    if self.modify_leg(leg) > 0:
                        if self.calculate():
                            self.plot_value(leg)
                else:
                    if self.modify_leg(0):
                        if self.calculate():
                            self.plot_value(0)
            elif selection == '5':
                if len(self.strategy.legs) > 0:
                    if self.calculate():
                        self.plot_value(0)
            elif selection == '6':
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = int(input('Enter Leg: ')) - 1
                    self.plot_value(leg)
                else:
                    self.plot_value(0)
            elif selection == '7':
                self.enter_options()
            elif selection == '8':
                break
            else:
                u.print_error('Unknown operation selected')


    def calculate(self):
        try:
            self.strategy.calculate()
            return True
        except:
            return False


    def analyze(self):
        '''TODO'''
        self.strategy.analyze()
        self.plot_analysis()


    def plot_value(self, leg):
        '''TODO'''

        if leg < len(self.strategy.legs):
            print(u.delimeter(f'Value: {self.strategy.legs[leg].symbol}', True) + '\n')

            table = self.strategy.legs[leg].table
            if table is not None:
                rows, cols = table.shape

                if rows > MAX_ROWS:
                    rows = MAX_ROWS
                else:
                    rows = -1

                if cols > MAX_COLS:
                    cols = MAX_COLS
                else:
                    cols = -1

                # We need to compress the table
                if rows > 0 or cols > 0:
                    table = self.strategy.legs[leg].compress_table(rows, cols)

                print(table)
            else:
                u.print_error('No table')
        else:
            u.print_error('Invalid leg')


    def plot_analysis(self):
        '''TODO'''

        if len(self.strategy.legs) > 0:
            print(u.delimeter(f'Analysis: {self.strategy.ticker} ({self.strategy.legs[0].symbol.short_name}) {str(self.strategy).title()}', True) + '\n')

            table = self.strategy.analysis.table
            if table is not None:
                rows, cols = table.shape

                if rows > MAX_ROWS:
                    rows = MAX_ROWS
                else:
                    rows = -1

                if cols > MAX_COLS:
                    cols = MAX_COLS
                else:
                    cols = -1

                # See if we need to compress the table
                if rows > 0 or cols > 0:
                    table = self.strategy.analysis.compress_table(rows, cols)

                print(table)
                print(self.strategy.analysis)
            else:
                u.print_error('No table')
        else:
            u.print_error('No option legs configured')


    def write_legs(self, leg=-1, delimeter=True):
        '''TODO'''
        if delimeter:
            print(u.delimeter('Option Leg Values', True))

        if len(self.strategy.legs) < 1:
            print('No legs configured')
        elif leg < 0:
            for index in range(0, len(self.strategy.legs), 1):
                # Recursive call to output each leg
                self.write_legs(index, False)
        elif leg < len(self.strategy.legs):
            output = f'{leg+1}: {self.strategy.legs[leg]}'
            print(output)
        else:
            u.print_error('Invalid leg')


    def reset(self):
        '''TODO'''
        self.strategy.reset()


    def enter_symbol(self):
        '''TODO'''
        success = True
        ticker = input('Please enter symbol: ').upper()
        vol = -1.0
        div = 0.0

        menu_items = {
            '1': 'Specify Volatility',
            '2': 'Specify Dividend',
            '3': 'Done'
        }

        while True:
            print('\nSelect Option')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                vol = float(input('Please enter volatility: '))
            elif selection == '2':
                div = float(input('Please enter average dividend: '))
            elif selection == '3':
                break
            else:
                u.print_error('Unknown operation selected')

        return self.strategy.set_symbol(ticker, vol, div)


    def enter_strategy(self):
        '''TODO'''

        menu_items = {
            '1': 'Call',
            '2': 'Put',
            '3': 'Vertical',
            '4': 'Cancel',
        }

        modified = False
        while True:
            print('\nSelect Strategy')
            print('---------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.strategy = Call(self.strategy.ticker)
                modified = True
                break
            if selection == '2':
                self.strategy = Put(self.strategy.ticker)
                modified = True
                break
            if selection == '3':
                self.strategy = Vertical(self.strategy.ticker)
                modified = True
                break
            if selection == '4':
                break

            u.print_error('Unknown strategy selected')

        return modified


    def modify_leg(self, leg):
        '''TODO'''

        quantity = self.strategy.legs[leg].quantity
        call_put = self.strategy.legs[leg].call_put
        long_short = self.strategy.legs[leg].long_short
        strike = self.strategy.legs[leg].strike
        expiry = self.strategy.legs[leg].expiry

        changed = False

        while True:
            menu_items = {
                '1': f'Quantity ({quantity})',
                '2': f'Call/Put ({call_put})',
                '3': f'Buy/Write ({long_short})',
                '4': f'Strike (${strike:.2f})',
                '5': f'Expiration ({expiry:%Y/%m/%d})',
                '6': 'Done',
                '7': 'Cancel',
            }

            self.write_legs()

            print('\nSpecify Leg')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                choice = input('Enter Quantity: ')
                if choice.isnumeric():
                    quantity = int(choice)
                else:
                    print('Invalid option')
            elif selection == '2':
                choice = input('Call (c) or Put (p): ')
                if 'c' in choice:
                    call_put = 'call'
                elif 'p' in choice:
                    call_put = 'put'
                else:
                    print('Invalid option')
            elif selection == '3':
                choice = input('Buy (b) or Write (w): ')
                if 'b' in choice:
                    long_short = 'long'
                elif 'w' in choice:
                    long_short = 'short'
                else:
                    print('Invalid option')
            elif selection == '4':
                choice = input('Enter Strike: ')
                if choice.isnumeric():
                    strike = float(choice)
                else:
                    print('Invalid option')
            elif selection == '5':
                pass
            elif selection == '6':
                changed = self.strategy.legs[leg].modify_values(quantity, call_put, long_short, strike, expiry)
                break
            elif selection == '7':
                break
            else:
                u.print_error('Unknown operation selected')

        return changed


    def enter_options(self):
        '''TODO'''

        menu_items = {
            '1': 'Pricing Method',
            '2': 'Cancel',
        }

        while True:
            print('\nSpecify Option')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.enter_method()
            elif selection == '2':
                break


    def enter_method(self):
        '''TODO'''

        menu_items = {
            '1': 'Black-Scholes',
            '2': 'Monte Carlo',
            '3': 'Cancel',
        }

        modified = True
        while True:
            print('\nSpecify Method')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.strategy.pricing_method = 'black-scholes'
                break
            if selection == '2':
                self.strategy.pricing_method = 'monte-carlo'
                break
            if selection == '3':
                break

            u.print_error('Unknown method selected')


    def _load_strategy(self, ticker, strategy, direction):
        modified = False

        try:
            if strategy.lower() == 'call':
                modified = True
                self.strategy = Call(ticker, direction)
                self.analyze()
            elif strategy.lower() == 'put':
                modified = True
                self.strategy = Put(ticker, direction)
                self.analyze()
            elif strategy.lower() == 'vertical':
                modified = True
                self.strategy = Vertical(ticker, direction)
                self.analyze()
            else:
                u.print_error('Unknown argument')
        except:
            u.print_error(sys.exc_info()[1], True)
            return False

        return modified


    def _validate(self):
        '''TODO'''
        return True


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Option Strategy Analyzer')
    subparser = parser.add_subparsers(help='Specify a command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Loads a strategy and direction')
    parser_a.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')
    parser_a.add_argument('-s', '--strategy', help='Load and analyze strategy', required=False, choices=['call', 'put', 'vertical'], default='call')
    parser_a.add_argument('-d', '--direction', help='Specify the direction', required=False, choices=['long', 'short'], default='long')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Executes a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'strategy' in command.keys():
        Interface(ticker=command['ticker'], strategy=command['strategy'], direction=command['direction'])
    elif 'script' in command.keys():
        Interface('FB', script=command['script'])
    else:
        Interface('MSFT')
