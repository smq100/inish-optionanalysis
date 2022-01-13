import time
import threading
import logging

import data as d
from analysis.correlate import Correlate
from data import store as store
from utils import ui


_logger = ui.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, coor: str = ''):
        self.list = coor.upper()
        self.coorelate: Correlate = None
        self.exchanges = [e['abbreviation'] for e in d.EXCHANGES]
        self.indexes = [i['abbreviation'] for i in d.INDEXES]
        self.tickers: list[str] = []

        if not coor:
            self.main_menu()
        elif store.is_list(self.list):
            self.main_menu(selection=1)
        else:
            ui.print_error('Invalid list specified')

    def main_menu(self, selection=0):
        while True:
            menu_items = {
                '1': 'Compute Coorelation',
                '2': 'Best Coorelation',
                '3': 'Least Coorelation',
                '4': 'ticker Coorelation',
                '0': 'Exit'
            }

            if selection == 0:
                selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)

            if selection == 1:
                self.compute_coorelation()
            elif selection == 2:
                self.get_best_coorelation()
            elif selection == 3:
                self.get_least_coorelation()
            elif selection == 4:
                self.get_ticker_coorelation()
            elif selection == 0:
                break

            selection = 0

    def compute_coorelation(self, progressbar=True):
        if not self.list:
            self.list = self._get_list()

        if self.list:
            self.tickers = store.get_tickers(self.list)
            self.coorelate = Correlate(self.tickers)

            self.task = threading.Thread(target=self.coorelate.compute_correlation)
            self.task.start()

            if progressbar:
                print()
                self._show_progress('Progress', '')

            ui.print_message(f'Coorelation Among {self.list} Symbols')
            print(self.coorelate.correlation)

    def get_best_coorelation(self):
        if not self.coorelate:
            ui.print_error('Run coorelation first')
        elif not self.coorelate:
            ui.print_error('Run coorelation first')
        else:
            ui.print_message(f'Best Coorelations in {self.list}')
            best = self.coorelate.get_sorted_coorelations(20, True)
            for item in best:
                print(f'{item[0]}/{item[1]:<5}\t{item[2]:.4f}')

    def get_least_coorelation(self):
        if not self.coorelate:
            ui.print_error('Run coorelation first')
        elif not self.coorelate:
            ui.print_error('Run coorelation first')
        else:
            ui.print_message(f'Least Coorelations in {self.list}')
            best = self.coorelate.get_sorted_coorelations(20, False)
            for item in best:
                print(f'{item[0]}/{item[1]:<5}\t{item[2]:.4f}')

    def get_ticker_coorelation(self):
        if not self.coorelate:
            ui.print_error('Run coorelation first')
        elif not self.coorelate:
            ui.print_error('Run coorelation first')
        else:
            ticker = ui.input_text('Enter symbol: ').upper()
            if not store.is_ticker(ticker):
                ui.print_error('Invalid symbol')
            else:
                df = self.coorelate.get_ticker_coorelation(ticker)
                ui.print_message(f'Highest correlations to {ticker}')
                for sym, val in df[-1:-11:-1].iteritems():
                    print(f'{sym:>5}: {val:.5f}')

                ui.print_message(f'Lowest correlations to {ticker}')
                for sym, val in df[:10].iteritems():
                    print(f'{sym:>5}: {val:.5f}')

    def _get_list(self):
        list = ''
        menu_items = {}
        for i, exchange in enumerate(self.exchanges):
            menu_items[f'{i+1}'] = f'{exchange}'
        for i, index in enumerate(self.indexes, i):
            menu_items[f'{i+1}'] = f'{index}'
        menu_items['0'] = 'Cancel'

        select = ui.menu(menu_items, 'Select exchange, or 0 to cancel: ', 0, i+1)
        if select > 0:
            list = menu_items[f'{select}']

        return list

    def _show_progress(self, prefix, suffix):
        while not self.coorelate.task_error:
            pass

        if self.coorelate.task_error == 'None':
            total = self.coorelate.task_total
            ui.progress_bar(self.coorelate.task_completed, self.coorelate.task_total, prefix=prefix, suffix=suffix, reset=True)

            while self.task.is_alive and self.coorelate.task_error == 'None':
                time.sleep(0.20)
                completed = self.coorelate.task_completed
                ticker = self.coorelate.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, suffix=suffix, ticker=ticker)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Analysis')
    parser.add_argument('-c', '--coorelate', help='Coorelate the list')

    command = vars(parser.parse_args())
    if command['coorelate']:
        Interface(coor=command['coorelate'])
    else:
        Interface()
