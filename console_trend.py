import time
import threading
import logging

import argparse
import matplotlib.pyplot as plt

from analysis.support_resistance import SupportResistance
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, tickers: list[str] = [], days: int = 365, quick: bool = False, exit: bool = False):
        self.tickers = [t.upper() for t in tickers]
        self.days = days
        self.quick = quick
        self.commands: list[dict] = []
        self.exit = exit
        self.trend: SupportResistance = None
        self.task: threading.Thread = None

        quit = False
        for ticker in tickers:
            if not store.is_ticker(ticker.upper()):
                ui.print_error(f'Invalid ticker: {ticker}')
                quit = True
                break

        if quit:
            pass
        elif self.exit:
            self.calculate_support_and_resistance()
        else:
            self.main_menu()

    def main_menu(self) -> None:
        self.commands = [
            {'menu': 'Change Ticker', 'function': self.select_ticker, 'condition': 'self.tickers', 'value': '", ".join(self.tickers)'},
            {'menu': 'Add Ticker', 'function': self.add_ticker, 'condition': '', 'value': ''},
            {'menu': 'Days', 'function': self.select_days, 'condition': 'True', 'value': 'self.days'},
            {'menu': 'Calculate Support & Resistance', 'function': self.calculate_support_and_resistance, 'condition': 'self.quick', 'value': '"quick"'},
        ]

        # Create the menu
        menu_items = {str(i+1): f'{self.commands[i]["menu"]}' for i in range(len(self.commands))}
        menu_items['0'] = 'Quit'

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while not self.exit:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items)-1)
            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                self.exit = True

    def select_ticker(self) -> None:
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.tickers = [ticker]
                else:
                    ui.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def add_ticker(self) -> None:
        valid = False

        while not valid:
            ticker = input('Please enter ticker, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.tickers += [ticker]
                else:
                    ui.print_error('Invalid ticker. Try again or enter 0 to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

    def calculate_support_and_resistance(self) -> None:
        if self.tickers:
            for ticker in self.tickers:
                if self.quick:
                    self.trend = SupportResistance(ticker, days=self.days)
                else:
                    methods = ['NSQUREDLOGN', 'NCUBED', 'HOUGHLINES', 'PROBHOUGH']
                    extmethods = ['NAIVE', 'NAIVECONSEC', 'NUMDIFF']
                    self.trend = SupportResistance(ticker, methods=methods, extmethods=extmethods, days=self.days)

                self.task = threading.Thread(target=self.trend.calculate)
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress()

                figure = self.trend.plot()
                plt.figure(figure)

            plt.show()
        else:
            ui.print_error('Enter a ticker before calculating')

    def show_progress(self) -> None:
        while not self.trend.task_state:
            pass

        print()
        if self.trend.task_state == 'None':
            ui.progress_bar(0, 0, suffix=self.trend.task_message, reset=True)

            while self.trend.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                ui.progress_bar(0, 0, suffix=self.trend.task_message)

            if self.trend.task_state == 'Hold':
                pass
            elif self.trend.task_state == 'Done':
                ui.print_message(f'{self.trend.task_state}: {self.trend.task_total} lines extracted in {self.trend.task_time:.1f} seconds', pre_creturn=2)
            else:
                ui.print_error(f'{self.trend.task_state}: Error extracting lines')
        else:
            ui.print_message(f'{self.trend.task_state}')


def main():
    parser = argparse.ArgumentParser(description='Technical Analysis')
    parser.add_argument('-t', '--tickers', metavar='ticker(s)', nargs='+', help='Run using tickers')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=365)
    parser.add_argument('-q', '--quick', help='Run quick analysis', action='store_true')
    parser.add_argument('-x', '--exit', help='Run trend analysis then exit (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(tickers=command['tickers'], days=int(command['days']), quick=command['quick'], exit=command['exit'])
    else:
        Interface(days=int(command['days']), quick=command['quick'])


if __name__ == '__main__':
    main()
