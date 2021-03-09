import sys, os, json
import logging
import datetime

import matplotlib.pyplot as plt

from pricing.fetcher import validate_ticker
from analysis.technical import TechnicalAnalysis
from analysis.trend import SupportResistance, Line
from utils import utils as u


logger = u.get_logger(logging.WARNING)

class Interface:
    def __init__(self, ticker, script=None):
        ticker = ticker.upper()
        if validate_ticker(ticker):
            start = datetime.datetime.today() - datetime.timedelta(days=90)
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
                '3': 'Support & Resistance Chart',
                '4': 'Plot All',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 4)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.select_technical()
            elif selection == 3:
                self.get_trend_parameters()
            elif selection == 4:
                self.plot_all()
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
            '1': 'EMA',
            '2': 'RSI',
            '3': 'VWAP',
            '4': 'MACD',
            '5': 'Bollinger Bands',
            '0': 'Done',
        }

        while True:
            selection = u.menu(menu_items, 'Select Indicator', 0, 5)

            if selection == 1:
                interval = u.input_integer('Enter interval: ', 5, 200)
                df = self.technical.calc_ema(interval)
                print(u.delimeter(f'EMA {interval}', True))
                print(f'Yesterday: {df[-1]:.2f}')
                self.plot(df, f'EMA {interval}')

            if selection == 2:
                df = self.technical.calc_rsi()
                print(u.delimeter('RSI', True))
                print(f'Yesterday: {df[-1]:.2f}')

            if selection == 3:
                df = self.technical.calc_vwap()
                print(u.delimeter('VWAP', True))
                print(f'Yesterday: {df[-1]:.2f}')

            if selection == 4:
                df = self.technical.calc_macd()
                print(u.delimeter('MACD', True))
                print(f'Diff: {df.iloc[-1]["Diff"]:.2f}')
                print(f'MACD: {df.iloc[-1]["MACD"]:.2f}')
                print(f'Sig:  {df.iloc[-1]["Signal"]:.2f}')

            if selection == 5:
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
        show = True

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

                sup = sr.get_support()
                print(u.delimeter(f'{sr.ticker} Support & Resistance Levels (${sr.price:.2f})', True))
                for line in sup:
                    print(f'Support:    ${line.end_point:.2f} ({line.get_score():.2f})')

                res = sr.get_resistance()
                for line in res:
                    print(f'Resistance: ${line.end_point:.2f} ({line.get_score():.2f})')

                sr.plot(filename=filename, show=show)
                break

            if selection == 0:
                break

    def plot_all(self):
        df1 = self.technical.calc_ema(21)
        df2 = self.technical.calc_rsi()
        df3 = self.technical.calc_vwap()
        df4 = self.technical.calc_macd()
        df5 = self.technical.calc_bb()
        df1.plot(label='EMA')
        df2.plot(label='RSI')
        df3.plot(label='VWAP')
        df4.plot(label='MACD')
        df5.plot(label='BB')
        plt.legend()
        plt.show()


    def plot(self, df, title=''):
        if df is not None:
            plt.style.use('seaborn-whitegrid')
            plt.grid()
            plt.margins(x=0.1)
            plt.legend()
            if title:
                plt.title(title)
            df.plot()
            plt.show()


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
