import os.path
import webbrowser
import configparser
import pickle
import logging

from requests_oauthlib import OAuth1Session

from etrade.accounts.accounts import Accounts
from etrade.quotes.quotes import Quotes
from etrade.options.options import Options
from etrade.lookup.lookup import Lookup
from etrade.alerts.alerts import Alerts
from utils import ui

ui.get_logger(logging.WARNING, logfile='')

class Client:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('etrade/config.ini')
        self.base_url = self.config['DEFAULT']['PROD_BASE_URL']
        self.picklefile = 'session.pickle'

        # Get a new session, or use existing
        if os.path.exists(self.picklefile):
            with open(self.picklefile, 'rb') as session_file:
                self.session = pickle.load(session_file)

            # Test session with a dummy call to get a quote and authorize if required
            url = f'{self.base_url}/v1/market/quote/aapl'
            if not _validate_session(self.session, url):
                self.session = self.authorize()
        else:
            self.session = self.authorize()

    def main_menu(self):
        menu_items = {
            '1': 'Lookup Symbol',
            '2': 'Market Quotes',
            '3': 'Options Chain',
            '4': 'Account List',
            '5': 'User Alerts',
            '0': 'Exit'
        }

        while True:
            selection = ui.menu(menu_items, 'Select Operation', 0, 5)
            if selection == 1:
                lookup = Lookup(self.session, self.base_url)
                symbol = input('\nPlease enter symbol: ')
                lookup.lookup(symbol)
            elif selection == 2:
                quotes = Quotes(self.session, self.base_url)
                symbols = input('\nPlease enter stock symbol: ')
                quotes.quotes(symbols)
            elif selection == 3:
                options = Options(self.session, self.base_url)
                symbol = input('\nPlease enter option symbol: ')
                options.chain(symbol, strikes=3)
            elif selection == 4:
                accounts = Accounts(self.session, self.base_url)
                accounts.list()
            elif selection == 5:
                alerts = Alerts(self.session, self.base_url)
                alerts.alerts()
            elif selection == 0:
                break
            else:
                print('Unknown operation selected')

    def authorize(self):
        consumer_key = self.config['DEFAULT']['CONSUMER_KEY']
        consumer_secret = self.config['DEFAULT']['CONSUMER_SECRET']
        request_token_url = 'https://api.etrade.com/oauth/request_token'
        access_token_url = 'https://api.etrade.com/oauth/access_token'
        authorize_url = 'https://us.etrade.com/e/t/etws/authorize'

        etrade = OAuth1Session(
            consumer_key,
            consumer_secret,
            callback_uri='oob',
            signature_type='AUTH_HEADER',
        )
        token = etrade.fetch_request_token(request_token_url)

        # Construct callback URL and display page to retrieve verifier code
        formated_auth_url = '%s?key=%s&token=%s' % (
            authorize_url, consumer_key, token['oauth_token'])
        webbrowser.open(formated_auth_url)

        # Confirm code and get token
        code = input('Please accept agreement and enter text code from browser: ')
        token = etrade.fetch_access_token(access_token_url, verifier=code)

        # Create authorized session
        session = OAuth1Session(
            consumer_key,
            consumer_secret,
            token['oauth_token'],
            token['oauth_token_secret'],
            signature_type="AUTH_HEADER")

        # Store session for later use
        with open(self.picklefile, 'wb') as session_file:
            pickle.dump(session, session_file)

        return session

def _validate_session(session, url):
    response = session.get(url)
    return response is not None and response.status_code == 200


if __name__ == '__main__':
    client = Client()
    client.main_menu()
