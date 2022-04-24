import os.path
import pickle
import webbrowser
import configparser
from requests_oauthlib.oauth1_session import TokenRequestDenied

from requests_oauthlib import OAuth1Session

from utils import logger

_logger = logger.get_logger()

SANDBOX = False

config = configparser.ConfigParser()
picklefile = './etrade/auth/session.pickle'
base_url = ''
key = ''

def authorize() -> OAuth1Session:
    global base_url, key

    session = None

    config.read('./etrade/auth/config.ini')
    if SANDBOX:
        base_url = config['DEFAULT']['BASE_URL_SB']
        key = config['DEFAULT']['CONSUMER_KEY_SB']
    else:
        base_url = config['DEFAULT']['BASE_URL']
        key = config['DEFAULT']['CONSUMER_KEY']

    # Get a new session, or use existing
    if os.path.exists(picklefile):
        with open(picklefile, 'rb') as session_file:
            try:
                session = pickle.load(session_file)
                _logger.info(f'{__name__}: Loaded existing session')
            except Exception as e:
                session = None
            else:
                # Test session with a dummy call to get a quote and authorize if required
                url = f'{base_url}/v1/market/quote/aapl'
                if not _validate_session(session, url):
                    session = None

    if session is None:
        session = _authorize()

    return session


def _authorize() -> OAuth1Session:
    session = None

    if SANDBOX:
        consumer_key = config['DEFAULT']['CONSUMER_KEY_SB']
        consumer_secret = config['DEFAULT']['CONSUMER_SECRET_SB']
    else:
        consumer_key = config['DEFAULT']['CONSUMER_KEY']
        consumer_secret = config['DEFAULT']['CONSUMER_SECRET']

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
    formated_auth_url = '%s?key=%s&token=%s' % (authorize_url, consumer_key, token['oauth_token'])
    webbrowser.open(formated_auth_url)

    # Confirm code and get token
    code = input('Please accept agreement and enter text code from browser: ')

    try:
        token = etrade.fetch_access_token(access_token_url, verifier=code)

        # Create authorized session
        session = OAuth1Session(
            consumer_key,
            consumer_secret,
            token['oauth_token'],
            token['oauth_token_secret'],
            signature_type="AUTH_HEADER")

        # Store session for later use
        with open(picklefile, 'wb') as session_file:
                pickle.dump(session, session_file, protocol=pickle.HIGHEST_PROTOCOL)

        _logger.info(f'{__name__}: Created new session')

    except TokenRequestDenied:
        session = None
    except Exception as e:
        session = None

    return session

def _validate_session(session, url):
    response = session.get(url)
    return (response is not None and response.status_code == 200)
