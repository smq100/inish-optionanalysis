import sys, os, json
import logging
import datetime

from pricing.fetcher import validate_ticker
from analysis.technical import TechnicalAnalysis
from analysis.trend import SupportResistance, Line
from utils import utils as u


logger = u.get_logger(logging.WARNING)

class Interface():
    def __init__(self, ticker, script=None):
        ticker = ticker.upper()
        if validate_ticker(ticker):
            start = datetime.datetime.today() - datetime.timedelta(days=365)
            self.technical = TechnicalAnalysis(ticker, start=start)

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
            u.print_error('Invalid ticker symbol specified')

    def main_menu(self):
        while True:
            menu_items = {
                '1': f'Change Symbol ({self.technical.ticker})',
                '2': 'Technical Analysis',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.select_technical()
            elif selection == 0:
                break

    def select_symbol(self):
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = validate_ticker(ticker)
                if valid:
                    start = datetime.datetime.today() - datetime.timedelta(days=365)
                    self.technical = TechnicalAnalysis(ticker, start=start)
                else:
                    u.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_technical(self):
        menu_items = {
            '1': 'Support & Resistance',
            '2': 'EMA',
            '3': 'RSI',
            '4': 'VWAP',
            '5': 'MACD',
            '6': 'Bollinger Bands',
            '0': 'Done',
        }

        while True:
            selection = u.menu(menu_items, 'Select Indicator', 0, 6)

            if selection == 1:
                self.get_trend_parameters()

            if selection == 2:
                interval = u.input_integer('Enter interval: ', 5, 200)
                df = self.technical.calc_ema(interval)
                print(u.delimeter(f'EMA {interval}', True))
                print(f'Yesterday: {df[-1]:.2f}')

            if selection == 3:
                df = self.technical.calc_rsi()
                print(u.delimeter('RSI', True))
                print(f'Yesterday: {df[-1]:.2f}')

            if selection == 4:
                df = self.technical.calc_vwap()
                print(u.delimeter('VWAP', True))
                print(f'Yesterday: {df[-1]:.2f}')

            if selection == 5:
                df = self.technical.calc_macd()
                print(u.delimeter('MACD', True))
                print(f'Diff: {df.iloc[-1]["Diff"]:.2f}')
                print(f'MACD: {df.iloc[-1]["MACD"]:.2f}')
                print(f'Sig:  {df.iloc[-1]["Signal"]:.2f}')

            if selection == 6:
                df = self.technical.calc_bb()
                print(u.delimeter('Bollinger Band', True))
                print(f'High: {df.iloc[-1]["High"]:.2f}')
                print(f'Mid:  {df.iloc[-1]["Mid"]:.2f}')
                print(f'Low:  {df.iloc[-1]["Low"]:.2f}')

            if selection == 0:
                break

    def get_trend_parameters(self):
        days = 1000
        filename = ''
        show = False

        while True:
            name = filename if filename else 'none'
            menu_items = {
                '1': f'Number of Days ({days})',
                '2': f'Plot File Name ({name})',
                '3': f'Show Window ({show})',
                '4': 'Analyze',
                '0': 'Cancel'
            }

            selection = u.menu(menu_items, 'Select option', 0, 4)

            if selection == 1:
                days = u.input_integer('Enter number of days (0=max): ', 0, 9999)

            if selection == 2:
                filename = input('Enter filename: ')

            if selection == 3:
                show = True if u.input_integer('Show Window? (1=Yes, 0=No): ', 0, 1) == 1 else False

            if selection == 4:
                start = None
                if days > 0:
                    start = datetime.datetime.today() - datetime.timedelta(days=days)

                sr = SupportResistance(self.technical.ticker, start=start)
                sr.calculate()
                sr.plot(filename=filename, show=show)

                sup, res = sr.get_endpoints()
                print(u.delimeter('Support and Resistance Levels', True))
                for line in sup:
                    print(f'Support:    ${line:.2f}')
                for line in res:
                    print(f'Resistance: ${line:.2f}')
                break

            if selection == 0:
                break


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Technical Analysis')
    subparser = parser.add_subparsers(help='Specify the desired command')

    # Create the parser for the "load" command
    parser_a = subparser.add_parser('load', help='Load an operation')
    parser_a.add_argument('-t', '--ticker', help='Specify the ticker symbol', required=False, default='IBM')

    # Create the parser for the "execute" command
    parser_b = subparser.add_parser('execute', help='Execute a JSON command script')
    parser_b.add_argument('-f', '--script', help='Specify a script', required=False, default='script.json')

    command = vars(parser.parse_args())

    if 'script' in command.keys():
        Interface('IBM', script=command['script'])
    elif 'ticker' in command.keys():
        Interface(command['ticker'])
    else:
        Interface('MSFT')
