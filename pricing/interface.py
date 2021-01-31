''' TODO '''
import pandas as pd

from strategy import Strategy, Leg
import utils


class Interface():
    '''TODO'''

    def __init__(self):
        self.strategy = Strategy()
        self.leg = Leg()

        pd.options.display.float_format = '{:,.2f}'.format

    def main_menu(self):
        '''Displays opening menu'''

        menu_items = {
            '1': 'Specify Symbol',
            '2': 'Specify Strategy',
            '3': 'Configure Leg',
            '4': 'Calculate',
            '5': 'Plot Value',
            '6': 'Plot Profit',
            '7': 'Change Pricing Method',
            '8': 'Exit'
        }

        while True:
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
                leg = self.enter_leg()
                if leg > 0:
                    self.write_leg(-1)
            elif selection == '4':
                self.calculate()
                self.write_all()
            elif selection == '5':
                self.plot_value()
            elif selection == '6':
                self.plot_profit()
            elif selection == '7':
                self.enter_method()
            elif selection == '8':
                break
            else:
                print('Unknown operation selected')


    def calculate(self):
        '''TODO'''
        self.strategy.calculate_leg()


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
        self.write_all()


    def enter_strategy(self):
        '''TODO'''

        menu_items = {
            '1': 'Long Call',
            '2': 'Short Call',
            '3': 'Cancel',
        }

        while True:
            self.write_leg(-1)
            print('\nSelect Strategy')
            print('---------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.strategy.strategy = 'long_call'
                break
            if selection == '2':
                self.strategy.strategy = 'short_call'
                break
            if selection == '3':
                break

            print('Unknown strategy selected')


    def enter_leg(self):
        '''TODO'''

        menu_items = {
            '1': 'Quantity',
            '2': 'Call/Put',
            '3': 'Long/Short',
            '4': 'Strike',
            '5': 'Expiration',
            '6': 'Add Leg',
            '7': 'Cancel',
        }

        while True:
            self.write_leg(-1)
            print('\nSpecify Leg')
            print('-------------------------')

            leg = 0

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
                choice = input('Long (l) or Short (s): ')
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
            self.write_leg(-1)
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


    def plot_value(self):
        '''TODO'''
        print(utils.delimeter(f'Value ({self.strategy.pricing_method})', True) + '\n')
        self.write_info(False)
        print(self.strategy.table_value)


    def plot_profit(self):
        '''TODO'''
        print(utils.delimeter(f'Profit ({self.strategy.pricing_method})', True) + '\n')
        self.write_info(True)
        print(self.strategy.table_profit)


    def write_leg(self, leg, delimeter=True):
        '''TODO'''
        if delimeter:
            print(utils.delimeter('Strategy Legs', True))

        if leg < 0:
            for leg_index in range(0, len(self.strategy.legs), 1):
                self.write_leg(leg_index, False)
        elif leg < len(self.strategy.legs):
            output = f'{leg}: '\
                f'{self.strategy.legs[leg].quantity}, '\
                f'{self.strategy.legs[leg].long_short:5s} '\
                f'{self.strategy.legs[leg].call_put:5s} '\
                f'${self.strategy.legs[leg].strike:.2f} for '\
                f'{str(self.strategy.legs[leg].expiry)[:10]}'
            print(output)
        else:
            print('No legs configured')

    def write_all(self, delimiter=True):
        '''TODO'''
        if delimiter:
            print(utils.delimeter('Product', True))

        output = \
            f'{self.leg.quantity} '\
            f'{self.strategy.symbol["ticker"]} '\
            f'{str(self.leg.expiry)[:10]} '\
            f'${self.leg.strike:.2f} '\
            f'{self.leg.long_short} '\
            f'{self.leg.call_put} '\
            f'= ${self.strategy.legs[0].price:.2f} ({self.strategy.pricing_method})\n'
        print(output)

    def write_info(self, delimiter=True):
        '''TODO'''
        if delimiter:
            print(utils.delimeter('Product', True))

        output = \
            f'{self.leg.quantity} '\
            f'{self.strategy.symbol["ticker"]} '\
            f'{str(self.leg.expiry)[:10]} '\
            f'${self.leg.strike:.2f} '\
            f'{self.leg.long_short} '\
            f'{self.leg.call_put} '\
            f'= ${self.strategy.legs[0].price:.2f} ({self.strategy.pricing_method})'
        print(output)

        output = f'Volatility: {self.strategy.pricer.volatility*100:.1f}%\n'
        print(output)

    def _validate(self):
        '''TODO'''
        return True


if __name__ == '__main__':
    ui = Interface()
    ui.main_menu()
