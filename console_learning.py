import logging

from learning.predict import Prediction
from data import store as store
from utils import ui


_logger = ui.get_logger(logging.WARNING, logfile='')

class Interface:
    def __init__(self, ticker='', days=30, exit=False):
        self.ticker = ticker.upper()
        self.days = days
        self.exit = exit

        if days <= 0:
            raise ValueError('Invalid number of days')

        if not ticker:
            self.main_menu()
        elif store.is_ticker(self.ticker):
            self.main_menu(selection=2)
        else:
            ui.print_error('Invalid ticker specified')

    def main_menu(self, selection=0):
        while True:
            menu_items = {
                '1': 'Specify ticker',
                '2': 'Run Pricing Prediction',
                '0': 'Exit'
            }

            if self.ticker:
                menu_items['1'] = f'Specify ticker ({self.ticker})'

            if selection == 0:
                selection = ui.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.run_model()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

            selection = 0

    def run_model(self):
        if self.ticker:
            predict = Prediction(self.ticker, future=self.days)
            predict.prepare()
            predict.model()

            ui.print_message(f'Metrics for {self.ticker}')
            print(f'Accuracy: {predict.accuracy:.3e}')
            print(f'Loss: {predict.loss:.3e}')

            predict.test()
            predict.plot()
        else:
            ui.print_error('Please first specify ticker')

    def select_ticker(self):
        valid = False

        while not valid:
            ticker = input('Please enter ticker, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if not valid:
                    ui.print_error('Invalid ticker. Try again or select "0" to cancel')
            else:
                break

        if valid:
            self.ticker = ticker


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Learning')
    parser.add_argument('-t', '--ticker', help='Run using ticker')
    parser.add_argument('-f', '--future', help='Future days', default=30)
    parser.add_argument('-x', help='Exit after running (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        if command['x']:
            Interface(ticker=command['ticker'], days=int(command['future']), exit=True)
        else:
            Interface(ticker=command['ticker'], days=int(command['future']))
    else:
        Interface()
