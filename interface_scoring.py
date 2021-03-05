import sys, os, json
import logging
import datetime

from pricing.fetcher import validate_ticker
from analysis.scoring import ScoringAnalysis
from analysis.technical import TechnicalAnalysis
from analysis.trend import SupportResistance, Line
from utils import utils as u


logger = u.get_logger(logging.WARNING)


class Interface():
    def __init__(self, ticker, script=None):
        ticker = ticker.upper()
        if validate_ticker(ticker):
            start = datetime.datetime.today() - datetime.timedelta(days=365)
            self.scoring = ScoringAnalysis(ticker)

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
                '1': f'Change Symbol ({self.scoring.ticker})',
                '2': 'Scoring',
                '0': 'Exit'
            }

            selection = u.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.get_scoring()
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
                    self.scoring = ScoringAnalysis(ticker)
                else:
                    u.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def get_scoring(self):
        pass


if __name__ == '__main__':
    import argparse

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Scoring')
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
