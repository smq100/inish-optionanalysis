import datetime as dt
import logging
import webbrowser

import argparse
import pandas as pd
from tabulate import tabulate

import etrade.auth as auth
from etrade.accounts import Accounts
from etrade.quotes import Quotes
from etrade.options import Options
from etrade.lookup import Lookup
from etrade.alerts import Alerts
from utils import math as m
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


def auth_callback(url: str) -> str:
    webbrowser.open(url)
    code = ui.input_alphanum('Please accept agreement and enter text code from browser')
    return code


class Client:
    def __init__(self, quote: str = '', exit: bool = False):
        self.quote: str = quote
        self.exit: bool = exit
        self.commands: list[dict] = []
        self.account_index: int = -1
        self.account_name: str = ''
        self.accounts: Accounts

        auth.authorize(auth_callback)

        if auth.Session is None:
            ui.print_error('Invalid authorization')
        elif self.quote:
            self.main_menu(selection=5)
        else:
            self.main_menu()


    def main_menu(self, selection: int = 0) -> None:
        self.commands = [
            {'menu': 'Accounts', 'function': self.m_show_accounts, 'condition': 'self.account_name', 'value': 'self.account_name'},
            {'menu': 'Balance', 'function': self.m_show_balance, 'condition': '', 'value': ''},
            {'menu': 'Portfolio', 'function': self.m_show_portfolio, 'condition': '', 'value': ''},
            {'menu': 'Alerts', 'function': self.m_show_alerts, 'condition': '', 'value': ''},
            {'menu': 'Quotes', 'function': self.m_show_quotes, 'condition': '', 'value': ''},
            {'menu': 'Options Expiry', 'function': self.m_show_options_expiry, 'condition': '', 'value': ''},
            {'menu': 'Options Chain', 'function': self.m_show_options_chain, 'condition': '', 'value': ''},
            {'menu': 'Lookup Symbol', 'function': self.m_show_symbol, 'condition': '', 'value': ''},
        ]

        # Create the menu
        menu_items = {str(i+1): f'{self.commands[i]["menu"]}' for i in range(len(self.commands))}

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while True:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))
            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                break

    def m_show_accounts(self) -> None:
        self.accounts = Accounts()
        acct_table = self.accounts.list()

        if self.accounts.message == 'success':
            menu_items = {str(acct.Index+1): f'{acct.accountDesc}: {acct.accountId}' for acct in acct_table.itertuples()}

            selection = ui.menu(menu_items, 'Available Accounts', 0, len(menu_items), prompt='Select account, or 0 when done', cancel = 'Cancel')
            if selection > 0:
                self.account_index = selection - 1
                self.account_name = menu_items[str(selection)]
            else:
                self.account_index = -1
                self.account_name = ''

    def m_show_balance(self) -> None:
        if self.account_index >= 0:
            balance = self.accounts.balance(self.account_index)

            if balance:
                ui.print_message(f'Balance for {balance["accountId"]}', pre_creturn=1, post_creturn=1)
                print(f'Account Nickname: {balance.get("accountDescription", "")}')
                print(f'Account Type: {balance.get("accountType", 0.0)}')
                print(f'Net Account Value: ${balance.get("Computed", {}).get("RealTimeValues", {}).get("totalAccountValue", 0.0):,.2f}')
                print(f'Margin Buying Power: ${balance.get("Computed", {}).get("marginBuyingPower", 0.0):,.2f}')
                print(f'Cash Buying Power: ${balance.get("Computed", {}).get("cashBuyingPower"):,.2f}')
                print(f'Option Level: {balance.get("optionLevel", "error")}\n')

                if ui.input_yesno('Show JSON'):
                    print(self.accounts.raw)
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def m_show_portfolio(self) -> None:
        if self.account_index >= 0:
            portfolio = self.accounts.portfolio(self.account_index)

            if not portfolio.empty:
                ui.print_message('Portfolio', pre_creturn=1, post_creturn=1)
                for position in portfolio.itertuples():
                    print(f'{str(position.symbolDescription)}')
                    print(f'Qty={position.quantity}')
                    print(f'Price={position.Quick["lastTrade"]:,.02f}')
                    print(f'Paid={position.pricePaid:,.02f}')
                    print(f'Gain={position.totalGain:,.02f}')
                    print(f'Value={position.marketValue:,.02f}')
                    print()

                if ui.input_yesno('Show JSON'):
                    print(self.accounts.raw)
            else:
                ui.print_error(self.accounts.message)
        else:
            ui.print_error('Must first select an account')

    def m_show_alerts(self):
        alerts = Alerts()
        alert_data = alerts.alerts()

        if not alert_data.empty:
            ui.print_message('Alerts', pre_creturn=1, post_creturn=1)
            for item in alert_data.itertuples():
                if item:
                    timestamp = dt.datetime.fromtimestamp(item.createTime)
                    alert = f'ID: {item.id}'
                    alert += f', Time: {timestamp:%Y-%m-%d %H:%M:%S}'
                    alert += f', Subject: {item.subject}'
                    alert += f', Status: {item.status}\n'
                print(alert)

            if ui.input_yesno('Show JSON'):
                print(alerts.raw)
        else:
            ui.print_message(alerts.message)

    def m_show_symbol(self) -> None:
        symbol = ui.input_text('Please enter symbol').upper()
        lookup = Lookup()
        lookup_data = lookup.lookup(symbol)

        if not lookup_data.empty:
            ui.print_message(f'Security information for {symbol}', pre_creturn=1, post_creturn=1)
            for item in lookup_data.itertuples():
                if item:
                    print(f'Symbol: {item.symbol}')
                    print(f'Type: {item.type}')
                    print(f'Desc: {item.description}')

                print()

            if ui.input_yesno('Show JSON'):
                print(lookup.raw)
        else:
            ui.print_error(f'No information for {symbol} located')

    def m_show_quotes(self) -> None:
        quotes = Quotes()

        if not self.quote:
            tickers = ui.input_list('Please enter symbols separated with commas').upper()
        else:
            tickers = self.quote

        self.quote = ''
        quote_data = quotes.quote(tickers.split(','))

        if quotes.message == 'success':
            ui.print_message('Quotes', pre_creturn=1, post_creturn=1)
            for quote in quote_data:
                if quote is not None:
                    print(f'Date Time: {quote.get("dateTime", "")}')
                    print(f'Symbol: {quote.get("Product", "").get("symbol", "")}')
                    print(f'Security Type: {quote.get("Product", {}).get("securityType", "")}')
                    if 'All' in quote:
                        all = quote["All"]
                        print(f'Last Price: {all.get("lastTrade", "")}')
                        print(f'Today\'s Change: {all.get("changeClose", 0.0):,.3f}) ({all.get("changeClosePercentage", 0.0)}%)')
                        print(f'Open: {all.get("open", 0.0):,.2f}')
                        print(f'Previous Close: {all.get("previousClose", 0.0):,.2f}')
                        print(f'Bid (Size): {all.get("bid", 0.0):,.2f}x{all.get("bidSize")}')
                        print(f'Ask (Size): {all.get("ask", 0.0):,.2f}x{all.get("askSize")}')
                        print(f'Day\'s Range: {all.get("low", 0.0):,.2f} - {all.get("high", 0.0):,.2f}')
                        print(f'Volume: {all.get("totalVolume"):,}')
                    print()

            if ui.input_yesno('Show JSON'):
                print(quotes.raw)

        else:
            ui.print_error(quotes.message)

    def m_show_options_expiry(self) -> None:
        ticker = ui.input_text('Please enter symbol').upper()

        options = Options()
        expiry_data = options.expiry(ticker)

        if 'error' in options.message.lower():
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif expiry_data.empty:
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            ui.print_message('Options Chain', post_creturn=1)
            expiry_data['date'] = pd.to_datetime(expiry_data['date']).dt.strftime(ui.DATE_FORMAT)
            print(tabulate(expiry_data, headers=expiry_data.columns, tablefmt=ui.TABULATE_FORMAT))
            print()

            if ui.input_yesno('Show JSON'):
                print(options.raw)

    def m_show_options_chain(self) -> None:
        symbol = ui.input_text('Please enter symbol').upper()

        date = m.third_friday()
        options = Options()
        chain = options.chain(symbol, date.month, date.year)

        if 'error' in options.message.lower():
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif chain is None:
            message = options.message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            order = [
                'symbol',
                'type',
                'strikePrice',
                'lastPrice',
                'inTheMoney',
                'volume',
            ]

            chain = chain.reindex(columns=order)

            ui.print_message('Options Chain', post_creturn=1)
            chain_calls = chain[chain['type'] == 'call']
            print(tabulate(chain_calls, headers=chain_calls.columns, tablefmt=ui.TABULATE_FORMAT, floatfmt='.02f'))

            print()
            chain_puts = chain[chain['type'] == 'put']
            print(tabulate(chain_puts, headers=chain_puts.columns, tablefmt=ui.TABULATE_FORMAT, floatfmt='.02f'))
            print()

            if ui.input_yesno('Show JSON'):
                print(options.raw)


def main():
    parser = argparse.ArgumentParser(description='Database Management')
    parser.add_argument('-q', '--quote', help='Get a quote on the specified ticker', metavar='ticker', required=False, default='')
    parser.add_argument('-x', '--exit', help='Run the operation then exit', action='store_true')

    command = vars(parser.parse_args())

    Client(quote=command['quote'], exit=command['exit'])


if __name__ == '__main__':
    main()
