''' TODO '''

import sys, os, json
import datetime

import pandas as pd

from strategy.strategy import Leg
from strategy.call import Call
from strategy.put import Put
from strategy.vertical import Vertical
from options.chain import Chain
from utils import utils as u

MAX_ROWS = 50
MAX_COLS = 18

class Interface():
    '''TODO'''

    def __init__(self, ticker, strategy, direction, auto=None, script=None, exit=False):
        pd.options.display.float_format = '{:,.2f}'.format

        ticker = ticker.upper()
        self.chain = Chain(ticker)

        if auto is not None:
            if self._load_strategy(ticker, auto, direction):
                if not exit:
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
            if not exit:
                expiry = datetime.datetime.today() + datetime.timedelta(days=14)
                self.strategy = Call(ticker, strategy, direction, 1, expiry)
                self.main_menu()
            else:
                u.print_error('Nothing to do')


    def main_menu(self):
        '''Displays opening menu'''

        while True:
            menu_items = {
                '1': f'Specify Symbol ({self.strategy.ticker})',
                '2': f'Specify Strategy ({self.strategy})',
                '3': 'Calculate Values',
                '4': 'Analyze Stategy',
                '5': 'Modify Leg',
                '6': 'Plot Leg Values',
                '7': 'Option Chains',
                '8': 'Settings',
                '9': 'Exit'
            }

            self.write_legs()

            print('\nSelect Operation')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 9)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.select_strategy()
            elif selection == 3:
                if len(self.strategy.legs) > 0:
                    if self.calculate():
                        self.plot_value(0)
            elif selection == 4:
                self.analyze()
            elif selection == 5:
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = u.input_integer('Enter Leg: ', 1, 2) - 1
                    if self.modify_leg(leg) > 0:
                        if self.calculate():
                            self.plot_value(leg)
                else:
                    if self.modify_leg(0):
                        if self.calculate():
                            self.plot_value(0)
            elif selection == 6:
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = u.input_integer('Enter Leg: ', 1, 2) - 1
                    self.plot_value(leg)
                else:
                    self.plot_value(0)
            elif selection == 7:
                self.select_chain_operation()
            elif selection == 8:
                self.select_settings()
            elif selection == 9:
                break


    def calculate(self):
        try:
            self.strategy.calculate()
            return True
        except:
            return False


    def analyze(self):
        '''TODO'''
        self.strategy.analyze()
        self.write_legs()
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


    def select_symbol(self):
        '''TODO'''
        success = True
        ticker = input('Please enter symbol: ').upper()
        vol = 0.0
        div = 0.0

        while True:
            menu_items = {
                '1': f'Specify Volatility ({vol:.2f})',
                '2': f'Specify Dividend (${div:.2f})',
                '3': 'Done'
            }

            print('\nSelect Option')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 3)

            if selection == 1:
                vol = u.input_float('Please enter volatility: ', 0.0, 5.0)
            elif selection == 2:
                div = u.input_float('Please enter average dividend: ', 0.0, 999.0)
            elif selection == 3:
                break
            else:
                u.print_error('Unknown operation selected')

        self.chain = Chain(ticker)

        return self.strategy.set_symbol(ticker, vol, div)


    def select_strategy(self):
        '''TODO'''

        menu_items = {
            '1': 'Call',
            '2': 'Put',
            '3': 'Vertical',
            '4': 'Cancel',
        }

        # Select strategy
        strategy = ''
        modified = False
        while True:
            print('\nSelect strategy')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 4)

            if selection == 1:
                strategy = 'call'
                break
            if selection == 2:
                strategy = 'put'
                break
            if selection == 3:
                strategy = 'vert'
                break
            if selection == 4:
                break

            u.print_error('Unknown strategy selected')

        # Select width and expiry date
        if strategy:
            modified = True
            width = -1

            width = u.input_integer('Please select width: ', 1, 5)

            self.select_chain_expiry()

            if strategy == 'call':
                self.strategy = Call(self.strategy.ticker, 'call', 'long')
            elif strategy == 'put':
                self.strategy = Put(self.strategy.ticker, 'put', 'long')
            elif strategy == 'vert':
                self.strategy = Vertical(self.strategy.ticker, 'call', 'long')

        return modified


    def modify_leg(self, leg):
        '''TODO'''

        quantity = self.strategy.legs[leg].quantity
        product = self.strategy.legs[leg].product
        direction = self.strategy.legs[leg].direction
        strike = self.strategy.legs[leg].option.strike

        changed = False

        while True:
            menu_items = {
                '1': f'Quantity ({quantity})',
                '2': f'Call/Put ({product})',
                '3': f'Buy/Write ({direction})',
                '4': f'Strike (${strike:.2f})',
                '5': 'Done',
                '6': 'Cancel',
            }

            self.write_legs()

            print('\nSelect leg')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 6)

            if selection == 1:
                quantity = u.input_integer('Enter Quantity: ', 1, 100)
            elif selection == 2:
                choice = input('Call (c) or Put (p): ')
                if 'c' in choice:
                    product = 'call'
                elif 'p' in choice:
                    product = 'put'
                else:
                    print('Invalid option')
            elif selection == 3:
                choice = input('Buy (b) or Write (w): ')
                if 'b' in choice:
                    direction = 'long'
                elif 'w' in choice:
                    direction = 'short'
                else:
                    print('Invalid option')
            elif selection == 4:
                choice = input('Enter Strike: ')
                if choice.isnumeric() and choice > 0.0:
                    strike = float(choice)
                else:
                    print('Invalid option')
            elif selection == 5:
                changed = self.strategy.legs[leg].modify_values(quantity, product, direction, strike)
                break
            elif selection == 6:
                break

        return changed


    def select_chain_operation(self):
        while True:
            if self.chain.expire is not None:
                expiry = self.chain.expire
            else:
                expiry = 'None selected'

            menu_items = {
                '1': f'Select Expiry Date ({expiry})',
                '2': f'Select Calls',
                '3': f'Select Puts',
                '4': 'Done',
            }

            print('\nSelect operation')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 4)

            if selection == 1:
                self.select_chain_expiry()
            if selection == 2:
                self.select_option('call')
            if selection == 3:
                self.select_option('put')
            elif selection == 4:
                break


    def select_option(self, product):
        options = None
        if self.chain.expire is None:
            u.print_error('No expiry date delected')
        elif product == 'call':
            options = self.chain.get_chain('call')
        elif product == 'put':
            options = self.chain.get_chain('put')

        if options is not None:
            print('\nSelect option')
            print('-------------------------')
            for index, row in options.iterrows():
                chain = f'{index+1})\t'\
                    f'${row["strike"]:7.2f} '\
                    f'${row["lastPrice"]:7.2f} '\
                    f'ITM: {bool(row["inTheMoney"])}'
                print(chain)

            select = u.input_integer('Select option, or 0 to cancel: ', 0, index + 1)

            if select > 0:
                sel_row = options.iloc[select-1]
                self.strategy.legs[0].option.load_contract(sel_row['contractSymbol'])
                # print(self.strategy.legs[0].option)
        else:
            u.print_error('Invalid selection')


    def select_chain_expiry(self):
        expiry = self.chain.get_expiry()

        print('\nSelect expiration')
        print('-------------------------')
        for index, exp in enumerate(expiry):
            print(f'{index+1})\t{exp}')

        select = u.input_integer('Select expiration date: ', 1, index+1)
        self.chain.expire = expiry[select-1]

        return self.chain.expire


    def select_settings(self):
        '''TODO'''

        menu_items = {
            '1': 'Pricing Method',
            '2': 'Cancel',
        }

        while True:
            print('\nSelect Setting')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 2)

            if selection == 1:
                self.select_method()
            elif selection == 2:
                break


    def select_method(self):
        '''TODO'''

        menu_items = {
            '1': 'Black-Scholes',
            '2': 'Monte Carlo',
            '3': 'Cancel',
        }

        modified = True
        while True:
            print('\nSelect method')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = u.input_integer('Please select: ', 1, 3)

            if selection == '1':
                self.strategy.pricing_method = 'black-scholes'
                break
            if selection == '2':
                self.strategy.pricing_method = 'monte-carlo'
                break
            if selection == '3':
                break

            u.print_error('Unknown method selected')


    def _load_strategy(self, ticker, name, direction):
        modified = False

        # try:
        expiry = datetime.datetime.today() + datetime.timedelta(days=14)
        if name.lower() == 'call':
            modified = True
            self.strategy = Call(ticker, 'call', direction, 1, expiry)
            self.analyze()
        elif name.lower() == 'put':
            modified = True
            self.strategy = Put(ticker, 'put', direction, 1, expiry)
            self.analyze()
        elif name.lower() == 'vertc':
            modified = True
            self.strategy = Vertical(ticker, 'call', direction, 1, expiry)
            self.analyze()
        elif name.lower() == 'vertp':
            modified = True
            self.strategy = Vertical(ticker, 'put', direction, 1, expiry)
            self.analyze()
        else:
            u.print_error('Unknown argument')
        # except:
        #     u.print_error(sys.exc_info()[1], True)
        #     return False

        return modified


    def _validate(self):
        '''TODO'''
        return True


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Option Strategy Analyzer')
    subparser = parser.add_subparsers(help='Specify the desired command')

    parser.add_argument('-x', '--exit', help='Exit after running loaded strategy or script', action='store_true', required=False, default=False)

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Loads a strategy and direction')
    parser_a.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')
    parser_a.add_argument('-s', '--strategy', help='Load and analyze strategy', required=False, choices=['call', 'put', 'vertc', 'vertp'], default=None)
    parser_a.add_argument('-d', '--direction', help='Specify the direction', required=False, choices=['long', 'short'], default='long')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Executes a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'strategy' in command.keys():
        Interface(ticker=command['ticker'], strategy='call', direction=command['direction'], auto=command['strategy'], exit=command['exit'])
    elif 'script' in command.keys():
        Interface('FB', 'call', 'long', script=command['script'], exit=command['exit'])
    else:
        Interface('MSFT', 'call', 'long', exit=command['exit'])
