import datetime as dt
import logging

from requests_oauthlib import OAuth1Session

import etrade.auth.auth as auth
from etrade.accounts.accounts import Accounts
from etrade.quotes.quotes import Quotes
from etrade.options.options import Options
from etrade.lookup.lookup import Lookup
from etrade.alerts.alerts import Alerts
from utils import math as m
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Client:
    def __init__(self):
        self.session: OAuth1Session | None = None
        self.accounts = None
        self.account_index = -1
        self.account_name = ''

        if self.session is None:
            self.session = auth.authorize()

        if self.session is not None:
            self.main_menu()
        else:
            ui.print_error('Invalid authorizaton text')

    def main_menu(self) -> None:
        while True:
            menu_items = {
                '1': 'Accounts',
                '2': 'Balance',
                '3': 'Portfolio',
                '4': 'Orders',
                '5': 'Alerts',
                '6': 'Quotes',
                '7': 'Options Chain',
                '8': 'Options Expiry',
                '9': 'Lookup Symbol',
                '0': 'Exit'
            }

            if self.account_name:
                menu_items['1'] += f' ({self.account_name})'

            selection = ui.menu(menu_items, 'Select Operation', 0, len(menu_items)-1)
            if selection == 1:
                self.show_accounts()
            elif selection == 2:
                self.show_balance()
            elif selection == 3:
                self.show_portfolio()
            elif selection == 4:
                self.show_orders()
            elif selection == 5:
                self.show_alerts()
            elif selection == 6:
                self.show_quotes()
            elif selection == 7:
                self.show_options_chain()
            elif selection == 8:
                self.show_options_expiry()
            elif selection == 9:
                self.lookup()
            elif selection == 0:
                break
            else:
                print('Unknown operation selected')

    def show_accounts(self) -> None:
        self.accounts = Accounts(self.session)
        success, listing = self.accounts.list()

        if success == 'success':
            menu_items = {str(n+1): listing[n] for n in range(len(listing))}
            menu_items['0'] = 'Cancel'

            selection = ui.menu(menu_items, 'Select Accounts', 0, len(menu_items)-1)
            if selection > 0:
                self.account_index = selection - 1
                self.account_name = listing[selection-1]
            else:
                self.account_index = -1
                self.account_name = ''
        else:
            self.accounts = None

    def show_balance(self) -> None:
        if self.account_index >= 0:
            message, balance = self.accounts.balance(self.account_index)

            if balance:
                ui.print_message(f'Balance for {balance["accountId"]}')

                if 'accountDescription' in balance:
                    print(f'Account Nickname: {balance["accountDescription"]}')
                if 'accountType' in balance:
                    print(f'Account Type: {balance["accountType"]}')
                if 'Computed' in balance \
                        and 'RealTimeValues' in balance['Computed'] \
                        and 'totalAccountValue' in balance['Computed']['RealTimeValues']:
                    print(f'Net Account Value: ${balance["Computed"]["RealTimeValues"]["totalAccountValue"]:,.2f}')
                if 'Computed' in balance \
                        and 'marginBuyingPower' in balance['Computed']:
                    print(f'Margin Buying Power: ${balance["Computed"]["marginBuyingPower"]:,.2f}')
                if 'Computed' in balance \
                        and 'cashBuyingPower' in balance['Computed']:
                    print(f'Cash Buying Power: ${balance["Computed"]["cashBuyingPower"]:,.2f}')
                if 'accountDescription' in balance:
                    print(f'Option Level: {balance["optionLevel"]}')
            else:
                ui.print_error(message)
        else:
            ui.print_error('Must first select an account')

    def show_portfolio(self) -> None:
        if self.account_index >= 0:
            message, portfolio = self.accounts.portfolio(self.account_index)

            if portfolio:
                ui.print_message('Portfolio')
                for acct_portfolio in portfolio['PortfolioResponse']['AccountPortfolio']:
                    if acct_portfolio is not None and 'Position' in acct_portfolio:
                        for position in acct_portfolio['Position']:
                            if position is not None:
                                print_str = ''
                                if 'symbolDescription' in position:
                                    print_str += f'{str(position["symbolDescription"])}'
                                if 'quantity' in position:
                                    print_str += f', Q: {position["quantity"]}'
                                if 'Quick' in position and 'lastTrade' in position['Quick']:
                                    print_str += f', Price: {position["Quick"]["lastTrade"]:,.2f}'
                                if 'pricePaid' in position:
                                    print_str += f', Paid: {position["pricePaid"]:,.2f}'
                                if 'totalGain' in position:
                                    print_str += f', Gain: {position["totalGain"]:,.2f}'
                                if 'marketValue' in position:
                                    print_str += f', Value: {position["marketValue"]:,.2f}'

                                print(print_str)
            else:
                ui.print_error(message)
        else:
            ui.print_error('Must first select an account')

    def show_orders(self) -> None:
        if self.account_index >= 0:
            ui.print_error('TODO')
        else:
            ui.print_error('Must first select an account')

    def show_alerts(self):
        alerts = Alerts(self.session)
        message, alert_data = alerts.alerts()

        if alert_data:
            alert = ''
            ui.print_message('Alerts')
            for item in alert_data['AlertsResponse']['Alert']:
                if item is not None and 'id' in item:
                    alert += f'ID: {item["id"]}'
                if item is not None and 'createTime' in item:
                    timestamp = dt.datetime.fromtimestamp(item['createTime']).strftime('%Y-%m-%d %H:%M:%S')
                    alert += f', Time: {timestamp}'
                if item is not None and 'subject' in item:
                    alert += f', Subject: {item["subject"]}'
                if item is not None and 'status' in item:
                    alert += f', Status: {item["status"]}'

                print(alert)
        else:
            ui.print_message(message)

    def lookup(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()
        lookup = Lookup(self.session)
        message, lookup_data = lookup.lookup(symbol)

        if lookup_data is not None:
            out = ''
            ui.print_message(f'Security information for {symbol}')
            for item in lookup_data['LookupResponse']['Data']:
                if item is not None and 'symbol' in item:
                    out += f'Symbol: {item["symbol"]}'
                if item is not None and 'type' in item:
                    out += f', Type: {item["type"]}'
                if item is not None and 'description' in item:
                    out += f', Desc: {item["description"]}'
                print(out)
        else:
            ui.print_error(message)

    def show_quotes(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()
        quotes = Quotes(self.session)
        message, quote_data = quotes.quote(symbol)

        if quote_data is not None:
            ui.print_message('Quotes')
            for quote in quote_data['QuoteResponse']['QuoteData']:
                if quote is not None:
                    if 'dateTime' in quote:
                        print(f'Date Time: {quote["dateTime"]}')
                    if 'Product' in quote and 'symbol' in quote['Product']:
                        print(f'Symbol: {quote["Product"]["symbol"]}')
                    if 'Product' in quote and 'securityType' in quote['Product']:
                        print(f'Security Type: {quote["Product"]["securityType"]}')
                    if 'All' in quote:
                        if 'lastTrade' in quote['All']:
                            print(f'Last Price: {quote["All"]["lastTrade"]}')
                        if 'changeClose' in quote['All'] and 'changeClosePercentage' in quote['All']:
                            print(f"Today's Change: {quote['All']['changeClose']:,.3f} ({quote['All']['changeClosePercentage']}%)")
                        if 'open' in quote['All']:
                            print(f'Open: {quote["All"]["open"]:,.2f}')
                        if 'previousClose' in quote['All']:
                            print(f'Previous Close: {quote["All"]["previousClose"]:,.2f}')
                        if 'bid' in quote['All'] and 'bidSize' in quote['All']:
                            print(f'Bid (Size): {quote["All"]["bid"]:,.2f} x{quote["All"]["bidSize"]}')
                        if 'ask' in quote['All'] and 'askSize' in quote['All']:
                            print(f'Ask (Size): {quote["All"]["ask"]:,.2f} x{quote["All"]["askSize"]}')
                        if 'low' in quote['All'] and 'high' in quote['All']:
                            print(f"Day's Range: {quote['All']['low']} - {quote['All']['high']}")
                        if 'totalVolume' in quote['All']:
                            print(f'Volume: {quote["All"]["totalVolume"]:,}')
        else:
            ui.print_error(message)

    def show_options_chain(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()

        date = m.third_friday()
        options = Options(self.session)
        message, chain_data = options.chain(symbol, date.month, date.year)

        if 'error' in message.lower():
            message = message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif chain_data is None:
            message = message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            ui.print_message('Options Chain')
            for pair in chain_data['OptionChainResponse']['OptionPair']:
                if pair['Call'] is not None:
                    out = ''
                    ask_bid = ''

                    call = pair['Call']
                    if 'displaySymbol' in call:
                        out += f'{call["displaySymbol"]} '
                    if 'ask' in call:
                        ask_bid = f' ask:${call["ask"]:.2f}'
                    if 'askSize' in call:
                        ask_bid += f'x{call["askSize"]}'
                        out += f'{ask_bid:15s}'
                    if 'bid' in call:
                        ask_bid = f' bid:${call["bid"]:.2f}'
                    if 'bidSize' in call:
                        ask_bid += f'x{call["bidSize"]}'
                        out += f'{ask_bid:15s}'
                    if 'inTheMoney' in call:
                        out += f' ITM:{call["inTheMoney"]}'
                    print(out)

                if pair['Put'] is not None:
                    out = ''
                    ask_bid = ''

                    put = pair['Put']
                    if 'displaySymbol' in put:
                        out += f'{put["displaySymbol"]}  '
                    if 'ask' in put:
                        ask_bid = f' ask:${put["ask"]:.2f}'
                    if 'askSize' in put:
                        ask_bid += f'x{put["askSize"]}'
                        out += f'{ask_bid:15s}'
                    if 'bid' in put:
                        ask_bid = f' bid:${put["bid"]:.2f}'
                    if 'bidSize' in put:
                        ask_bid += f'x{put["bidSize"]}'
                        out += f'{ask_bid:15s}'
                    if 'inTheMoney' in put:
                        out += f' ITM:{put["inTheMoney"]}'
                    print(out)

    def show_options_expiry(self) -> None:
        symbol = ui.input_text('Please enter symbol: ').upper()

        options = Options(self.session)
        message, expiry_data = options.expiry(symbol)

        if 'error' in message.lower():
            message = message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        elif expiry_data is None:
            message = message.replace('Error ', '')
            message = message.replace('\n', '')
            ui.print_error(message)
        else:
            ui.print_message('Options Chain')
            for pair in expiry_data['OptionExpireDateResponse']['ExpirationDate']:
                print(pair)

def main():
    client = Client()

if __name__ == '__main__':
    main()
