''' TODO '''

import sys, os, json
import datetime

import pandas as pd

from strategy.strategy import Leg
from strategy.call import Call
from strategy.put import Put
from strategy.vertical import Vertical
from pricing.fetcher import validate_ticker
from options.chain import Chain
from utils import utils as u

MAX_ROWS = 50
MAX_COLS = 18

class Interface():
    '''TODO'''

    def __init__(self, ticker, strategy, direction, autoload=None, script=None, exit=False):
        pd.options.display.float_format = '{:,.2f}'.format

        ticker = ticker.upper()
        valid = validate_ticker(ticker)

        self.dirty_calculate = True
        self.dirty_analyze = True

        if valid:
            self.chain = Chain(ticker)

            if autoload is not None:
                if self.load_strategy(ticker, autoload, direction):
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
                    self.strategy = Call(ticker, strategy, direction)
                    self.calculate()
                    self.main_menu()
                else:
                    u.print_error('Nothing to do')
        else:
            u.print_error('Invalid ticker symbol specified')


    def main_menu(self):
        '''Displays opening menu'''

        while True:
            menu_items = {
                '1': f'Change Symbol ({self.strategy.ticker})',
                '2': f'Change Strategy ({self.strategy})',
                '3': 'Select Options',
                '4': 'Calculate Values',
                '5': 'Analyze Stategy',
                '6': 'Modify Leg',
                '7': 'View Options',
                '8': 'View Values',
                '9': 'Settings',
                '0': 'Exit'
            }

            if self.dirty_calculate:
                menu_items['4'] += ' *'

            if self.dirty_analyze:
                menu_items['5'] += ' *'

            if self.strategy.name == 'vertical':
                menu_items['3'] += f' '\
                    f'(L:${self.strategy.legs[0].option.strike:.2f}{self.strategy.legs[0].option.decorator}'\
                    f' S:${self.strategy.legs[1].option.strike:.2f}{self.strategy.legs[1].option.decorator})'
            else:
                menu_items['3'] += f' (${self.strategy.legs[0].option.strike:.2f}{self.strategy.legs[0].option.decorator})'

            self.view_legs()

            selection = self._menu(menu_items, 'Select Operation', 0, 9)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.select_strategy()
            elif selection == 3:
                if self.select_chain():
                    self.calculate()
                    self.view_options(0)
            elif selection == 4:
                if len(self.strategy.legs) > 0:
                    if self.calculate():
                        self.plot_value(0)
            elif selection == 5:
                self.analyze()
            elif selection == 6:
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
            elif selection == 7:
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = u.input_integer('Enter Leg: ', 1, 2) - 1
                    self.view_options(leg)
                else:
                    self.view_options(0)
            elif selection == 8:
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = u.input_integer('Enter Leg: ', 1, 2) - 1
                    self.plot_value(leg)
                else:
                    self.plot_value(0)
            elif selection == 9:
                self.select_settings()
            elif selection == 0:
                break


    def calculate(self):
        try:
            self.strategy.calculate()
            self.dirty_calculate = False
            return True
        except:
            return False


    def analyze(self):
        '''TODO'''
        errors = self.strategy.get_errors()
        if not errors:
            self.strategy.analyze()
            self.view_legs()
            self.plot_analysis()

            self.dirty_calculate = False
            self.dirty_analyze = False
        else:
            u.print_error(errors)


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
            print(u.delimeter(f'Analysis: {self.strategy.ticker} ({self.strategy.legs[0].symbol.company.info["shortName"]}) {str(self.strategy).title()}', True) + '\n')

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


    def view_legs(self, leg=-1, delimeter=True):
        '''TODO'''
        if delimeter:
            print(u.delimeter('Option Leg Values', True))

        if len(self.strategy.legs) < 1:
            print('No legs configured')
        elif leg < 0:
            for index in range(0, len(self.strategy.legs), 1):
                # Recursive call to output each leg
                self.view_legs(index, False)
        elif leg < len(self.strategy.legs):
            output = f'{leg+1}: {self.strategy.legs[leg]}'
            print(output)
        else:
            u.print_error('Invalid leg')


    def view_options(self, leg=-1, delimeter=True):
        if delimeter:
            print(u.delimeter('Option Specs', True))

        if len(self.strategy.legs) < 1:
            print('No legs configured')
        elif leg < 0:
            for index in range(0, len(self.strategy.legs), 1):
                # Recursive call to output each leg
                self.view_legs(index, False)
        elif leg < len(self.strategy.legs):
            output = f'{self.strategy.legs[leg].option}'
            print(output)
        else:
            u.print_error('Invalid leg')


    def reset(self):
        '''TODO'''
        self.strategy.reset()


    def select_symbol(self):
        '''TODO'''
        valid = False
        vol = 0.0
        div = 0.0

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = validate_ticker(ticker)
                if not valid:
                    u.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

        if valid:
            self.dirty_calculate = True
            self.dirty_analyze = True

            self.chain = Chain(ticker)
            self.load_strategy(ticker, 'call', 'long', False)
            u.print_message('The initial strategy has been set to a long call')


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
            selection = self._menu(menu_items, 'Select Strategy', 1, 4)

            if selection == 1:
                direction = u.input_integer('Long (1), or short (2): ', 1, 2)
                direction = 'long' if direction == 1 else 'short'
                self.strategy = Call(self.strategy.ticker, 'call', direction)

                self.dirty_calculate = True
                self.dirty_analyze = True
                modified = True
                break
            if selection == 2:
                direction = u.input_integer('Long (1), or short (2): ', 1, 2)
                direction = 'long' if direction == 1 else 'short'
                self.strategy = Put(self.strategy.ticker, 'put', direction)

                self.dirty_calculate = True
                self.dirty_analyze = True
                modified = True
                break
            if selection == 3:
                product = u.input_integer('Call (1), or Put (2): ', 1, 2)
                product = 'call' if product == 1 else 'put'
                direction = u.input_integer('Debit (1), or credit (2): ', 1, 2)
                direction = 'long' if direction == 1 else 'short'

                self.strategy = Vertical(self.strategy.ticker, product, direction)

                self.dirty_calculate = True
                self.dirty_analyze = True
                modified = True
                break
            if selection == 4:
                break

            u.print_error('Unknown strategy selected')

        return modified


    def select_chain(self):
        contract = ''

        # Go directly to get expire date if not already entered
        if self.chain.expire is None:
            ret = self.select_chain_expiry()
            if ret:
                self.strategy.update_expiry(ret)
                if self.strategy.name != 'vertical':
                    # Go directly to choose option if only one leg in strategy
                    if self.strategy.legs[0].option.product == 'call':
                        contract = self.select_chain_option('call')
                    else:
                        contract = self.select_chain_option('put')

                    # Load the new contract
                    if contract:
                        self.strategy.legs[0].option.load_contract(contract)


        if not contract:
            while True:
                if self.chain.expire is not None:
                    expiry = self.chain.expire
                else:
                    expiry = 'None selected'

                if self.strategy.legs[0].option.product == 'call':
                    product = 'Call'
                else:
                    product = 'Put'

                menu_items = {
                    '1': f'Select Expiry Date ({expiry})',
                    '2': f'Select {product} Option',
                    '3': 'Done',
                }

                if self.strategy.name == 'vertical':
                    menu_items['2'] = f'Select {product} Options'
                    menu_items['2'] += f' '\
                        f'(L:${self.strategy.legs[0].option.strike:.2f}{self.strategy.legs[0].option.decorator}'\
                        f' S:${self.strategy.legs[1].option.strike:.2f}{self.strategy.legs[1].option.decorator})'
                else:
                    menu_items['2'] += f' (${self.strategy.legs[0].option.strike:.2f}{self.strategy.legs[0].option.decorator})'

                selection = self._menu(menu_items, 'Select Operation', 0, 3)

                ret = True
                if selection == 1:
                    if self.select_chain_expiry():
                        self.strategy.update_expiry(ret)

                elif selection == 2:
                    if self.chain.expire is not None:
                        if self.strategy.name == 'vertical':
                            leg = u.input_integer('Long leg (1), or short (2): ', 1, 2) - 1
                        else:
                            leg = 0

                        if self.strategy.legs[leg].option.product == 'call':
                            contract = self.select_chain_option('call')
                        else:
                            contract = self.select_chain_option('put')

                        if contract:
                            ret = self.strategy.legs[leg].option.load_contract(contract)
                        else:
                            u.print_error('No option selected')

                        if self.strategy.name != 'vertical':
                            break
                    else:
                        u.print_error('Please first select expiry date')
                elif selection == 3:
                    break
                elif selection == 0:
                    break

                if not ret:
                    u.print_error('Error loading option. Please try again')

        return contract


    def select_chain_expiry(self):
        expiry = self.chain.get_expiry()

        print('\nSelect Expiration')
        print('-------------------------')
        for index, exp in enumerate(expiry):
            print(f'{index+1})\t{exp}')

        select = u.input_integer('Select expiration date, or 0 to cancel: ', 0, index+1)
        if select > 0:
            self.chain.expire = expiry[select-1]
            expiry = datetime.datetime.strptime(self.chain.expire, '%Y-%m-%d')

            self.dirty_calculate = True
            self.dirty_analyze = True
        else:
            expiry = None

        return expiry


    def select_chain_option(self, product):
        options = None
        contract = ''
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
                contract = sel_row['contractSymbol']

                self.dirty_calculate = True
                self.dirty_analyze = True
        else:
            u.print_error('Invalid selection')

        return contract


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

            self.view_legs()

            selection = self._menu(menu_items, 'Select Leg', 1, 6)

            if selection == 1:
                quantity = u.input_integer('Enter Quantity: ', 1, 100)
            elif selection == 2:
                choice = u.input_integer('Call (1) or Put (2): ', 1, 2)
                if choice == 1:
                    product = 'call'
                elif choice == 2:
                    product = 'put'
            elif selection == 3:
                choice = u.input_integer('Buy (1) or Write (2): ', 1, 2)
                if choice == 1:
                    direction = 'long'
                elif choice == 2:
                    direction = 'short'
                else:
                    print('Invalid option')
            elif selection == 4:
                strike = u.input_float('Enter Strike: ', 0.01, 999.0)
            elif selection == 5:
                changed = self.strategy.legs[leg].modify_values(quantity, product, direction, strike)
                self.dirty_calculate = True
                self.dirty_analyze = True
                break
            elif selection == 6:
                break

        return changed


    def select_settings(self):
        '''TODO'''

        while True:
            menu_items = {
                '1': f'Pricing Method ({self.strategy.legs[0].pricing_method.title()})',
                '0': 'Done',
            }

            selection = self._menu(menu_items, 'Select Setting', 0, 1)

            if selection == 1:
                self.select_method()
            elif selection == 0:
                break


    def select_method(self):
        '''TODO'''

        menu_items = {
            '1': 'Black-Scholes',
            '2': 'Monte Carlo',
            '0': 'Cancel',
        }

        modified = True
        while True:
            selection = self._menu(menu_items, 'Select Method', 0, 2)

            if selection == 1:
                self.strategy.pricing_method = 'black-scholes'
                self.strategy.set_pricing_method(self.strategy.pricing_method)
                self.dirty_calculate = True
                self.dirty_analyze = True
                break

            if selection == 2:
                self.strategy.pricing_method = 'monte-carlo'
                self.strategy.set_pricing_method(self.strategy.pricing_method)
                self.dirty_calculate = True
                self.dirty_analyze = True
                break

            if selection == 0:
                break

            u.print_error('Unknown method selected')


    def load_strategy(self, ticker, name, direction, analyze=True):
        modified = False

        # try:
        if name.lower() == 'call':
            modified = True
            self.strategy = Call(ticker, 'call', direction)
            if analyze:
                self.analyze()
        elif name.lower() == 'put':
            modified = True
            self.strategy = Put(ticker, 'put', direction)
            if analyze:
                self.analyze()
        elif name.lower() == 'vertc':
            modified = True
            self.strategy = Vertical(ticker, 'call', direction)
            if analyze:
                self.analyze()
        elif name.lower() == 'vertp':
            modified = True
            self.strategy = Vertical(ticker, 'put', direction)
            if analyze:
                self.analyze()
        else:
            u.print_error('Unknown argument')

        # except:
        #     u.print_error(sys.exc_info()[1], True)
        #     return False

        return modified


    def _menu(self, menu_items, header, minvalue, maxvalue):
        print(f'\n{header}')
        print('-----------------------------')

        option = menu_items.keys()
        for entry in option:
            print(f'{entry})\t{menu_items[entry]}')

        return u.input_integer('Please select: ', minvalue, maxvalue)


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
    parser_a = subparser.add_parser('load', help='Load a strategy')
    parser_a.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')
    parser_a.add_argument('-s', '--strategy', help='Load and analyze strategy', required=False, choices=['call', 'put', 'vertc', 'vertp'], default=None)
    parser_a.add_argument('-d', '--direction', help='Specify the direction', required=False, choices=['long', 'short'], default='long')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'strategy' in command.keys():
        Interface(ticker=command['ticker'], strategy='call', direction=command['direction'], autoload=command['strategy'], exit=command['exit'])
    elif 'script' in command.keys():
        Interface('FB', 'call', 'long', script=command['script'], exit=command['exit'])
    else:
        Interface('MSFT', 'call', 'long', exit=command['exit'])
