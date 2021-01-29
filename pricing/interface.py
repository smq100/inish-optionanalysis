''' TODO '''
import datetime
import pandas as pd
from european import EuropeanPricing


class Interface():
    '''TODO'''
    def __init__(self):
        pd.options.display.float_format = '{:,.2f}'.format
        self.pricer = None
        self.table_value = pd.DataFrame()
        self.table_profit = pd.DataFrame()

    def calculate(self, ticker, expiry_date, strike, method='black-scholes', dividend=0.0):
        '''TODO'''
        if method == 'black-scholes':
            self.pricer = EuropeanPricing(ticker, expiry_date, strike)

        call_price, put_price = self.pricer.calculate_prices()
        self.table_value = self.pricer.generate_value_table('call')
        self.table_profit = self.pricer.generate_profit_table(call_price, self.table_value)

    def main_menu(self):
        '''Displays opening menu'''

        menu_items = {
            '1': 'Specify Symbol',
            '2': 'Specify Strategy',
            '3': 'Specify Expiry',
            '4': 'Specify Strike',
            '5': 'Calculate',
            '6': 'Plot Value',
            '7': 'Plot Profit',
            '8': 'Exit'
        }

        while True:
            print('\nSelect Option')
            print('---------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                pass
            elif selection == '2':
                pass
            elif selection == '3':
                pass
            elif selection == '4':
                pass
            elif selection == '5':
                ui.calculate('AAPL', datetime.datetime(2021, 2, 12), 145)
            elif selection == '6':
                self.plot_value()
            elif selection == '7':
                self.plot_profit()
            elif selection == '8':
                break
            else:
                print('Unknown operation selected')

    def plot_value(self):
        '''TODO'''
        print('\n***** Value Table *****')
        print(self.table_value)

    def plot_profit(self):
        '''TODO'''
        print('\n***** Profit Table *****')
        print(self.table_profit)

if __name__ == '__main__':
    ui = Interface()
    ui.main_menu()
