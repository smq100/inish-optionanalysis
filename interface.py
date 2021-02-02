''' TODO '''
import sys
import pandas as pd

from utils import utils as u
from strategy.strategy import Strategy, Leg


class Interface():
    '''TODO'''

    def __init__(self, args=None):
        self.strategy = Strategy()
        self.leg = Leg()

        pd.options.display.float_format = '{:,.2f}'.format

        if args is not None:
            self._script(args)

    def main_menu(self):
        '''Displays opening menu'''

        menu_items = {
            '1': 'Specify Symbol',
            '2': 'Specify Strategy',
            '3': 'Analyze Stategy',
            '4': 'Add Leg',
            '5': 'Calculate Leg',
            '6': 'Plot Leg Value',
            '7': 'Change Pricing Method',
            '8': 'Exit'
        }

        while True:
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
                self.enter_strategy()
            elif selection == '3':
                self.analyze_strategy()
            elif selection == '4':
                leg = self.enter_leg()
            elif selection == '5':
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = input('Enter Leg: ')
                    self.calculate(int(leg)-1)
                else:
                    self.calculate(0)
            elif selection == '6':
                if len(self.strategy.legs) < 1:
                    print('No legs configured')
                elif len(self.strategy.legs) > 1:
                    leg = input('Enter Leg: ')
                    self.plot_value(int(leg)-1)
                else:
                    self.plot_value(0)
            elif selection == '7':
                self.enter_method()
            elif selection == '8':
                break
            else:
                print('Unknown operation selected')


    def calculate(self, leg):
        '''TODO'''
        if leg < 0:
            pass
        else:
            self.strategy.calculate_leg(leg)


    def reset(self):
        '''TODO'''
        self.strategy.reset()


    def enter_symbol(self):
        '''TODO'''
        ticker = input('Please enter symbol: ').upper()
        vol = -1.0
        div = 0.0

        menu_items = {
            '1': 'Specify Volitility',
            '2': 'Specify Dividend',
            '3': 'Back'
        }

        while True:
            print('\nSelect Option')
            print('-------------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                pass
            elif selection == '2':
                pass
            elif selection == '3':
                break
            else:
                print('Unknown operation selected')

        self.strategy.set_symbol(ticker, vol, div)


    def enter_strategy(self):
        '''TODO'''

        menu_items = {
            '1': 'Call',
            '2': 'Put',
            '2': 'Vertical',
            '3': 'Cancel',
        }

        while True:
            print('\nSelect Strategy')
            print('---------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.strategy.strategy = 'call'
                break
            if selection == '2':
                self.strategy.strategy = 'put'
                break
            if selection == '3':
                self.strategy.strategy = 'vertical'
                break
            if selection == '4':
                break

            print('Unknown strategy selected')


    def enter_leg(self):
        '''TODO'''

        menu_items = {
            '1': 'Quantity',
            '2': 'Call/Put',
            '3': 'Buy/Write',
            '4': 'Strike',
            '5': 'Expiration',
            '6': 'Add Leg',
            '7': 'Cancel',
        }

        while True:
            self.write_legs()
            print('\nSpecify Leg')
            print('-------------------------')

            leg = -1

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                choice = input('Enter Quantity: ')
                if choice.isnumeric():
                    self.leg.quantity = int(choice)
                else:
                    print('Invalid option')
            elif selection == '2':
                choice = input('Call (c) or Put (p): ')
                if 'c' in choice:
                    self.leg.call_put = 'call'
                elif 'p' in choice:
                    self.leg.call_put = 'put'
                else:
                    print('Invalid option')
            elif selection == '3':
                choice = input('Buy (b) or Write (w): ')
                if 'l' in choice:
                    self.leg.long_short = 'long'
                elif 's' in choice:
                    self.leg.long_short = 'short'
                else:
                    print('Invalid option')
            elif selection == '4':
                choice = input('Enter Strike: ')
                if choice.isnumeric():
                    self.leg.strike = float(choice)
                else:
                    print('Invalid option')
            elif selection == '5':
                pass
            elif selection == '6':
                leg = self.strategy.add_leg(self.leg.quantity, self.leg.call_put, self.leg.long_short, self.leg.strike, self.leg.expiry)
                break
            elif selection == '7':
                break
            else:
                print('Unknown operation selected')

        return leg


    def enter_method(self):
        '''TODO'''

        menu_items = {
            '1': 'Black-Scholes',
            '2': 'Monte Carlo',
            '3': 'Cancel',
        }

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

            print('Unknown method selected')


    def analyze_strategy(self):
        '''TODO'''
        dframe, legs = self.strategy.analyze_strategy()
        if dframe is not None:
            print(u.delimeter(f'Strategy Analysis ({self.strategy.strategy})', True) + '\n')
            # self.write_legs(legs-1)
            # print('')
            print(dframe)
        else:
            print('No option legs configured')


    def plot_value(self, leg):
        '''TODO'''
        print(u.delimeter(f'Value ({self.strategy.pricing_method})', True) + '\n')
        # self.write_legs(leg)
        # print('')
        print(self.strategy.legs[leg].table_value)


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
            output = f'{leg+1}: '\
                f'{self.strategy.legs[leg].quantity} '\
                f'{self.strategy.symbol["ticker"]:4s} '\
                f'{self.strategy.legs[leg].long_short:5s} '\
                f'{self.strategy.legs[leg].call_put:5s} '\
                f'${self.strategy.legs[leg].strike:.2f} for '\
                f'{str(self.strategy.legs[leg].expiry)[:10]}'

            if self.strategy.legs[leg].price > 0.0:
                output += f' = ${self.strategy.legs[leg].price:.2f}'
                output += f' (${self.strategy.legs[leg].spot:.2f}@{self.strategy.pricer.volatility*100:.1f}%)'

            print(output)
        else:
            print('Invalid leg')

    def _script(self, args):
        if args[0].lower() == 'c':
            self.strategy.strategy = 'call'

            self.leg.quantity = 1
            self.leg.call_put = 'call'
            self.leg.long_short = 'long'
            self.leg.strike = 130.0
            self.strategy.add_leg(self.leg.quantity, self.leg.call_put, self.leg.long_short, self.leg.strike, self.leg.expiry)

            self.analyze_strategy()

            self.main_menu()
        elif args[0].lower() == 'v':
            self.strategy.strategy = 'vertical'

            self.leg.quantity = 1
            self.leg.call_put = 'call'
            self.leg.long_short = 'long'
            self.leg.strike = 130.0
            self.strategy.add_leg(self.leg.quantity, self.leg.call_put, self.leg.long_short, self.leg.strike, self.leg.expiry)

            self.leg.long_short = 'short'
            self.leg.strike = 135.0
            self.strategy.add_leg(self.leg.quantity, self.leg.call_put, self.leg.long_short, self.leg.strike, self.leg.expiry)

            self.analyze_strategy()

            self.main_menu()
        else:
            print('Error: Unknown argument')


    def _validate(self):
        '''TODO'''
        return True


if __name__ == '__main__':
    args = sys.argv[1:]
    ui = Interface(args=args)

    if args is None:
        ui.main_menu()
