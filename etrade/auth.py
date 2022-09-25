from pathlib import Path
import pickle
import configparser
from requests_oauthlib.oauth1_session import TokenRequestDenied
from typing import Callable

from requests_oauthlib import OAuth1Session

from utils import logger

_logger = logger.get_logger()

SANDBOX = False

config = configparser.ConfigParser()
picklefile = './etrade/auth/session.pickle'
base_url = ''
key = ''

Session: OAuth1Session | None = None


def authorize(callback: Callable[[str], str]) -> OAuth1Session:
    global Session, base_url, key

    config.read('./etrade/auth/config.ini')
    if SANDBOX:
        base_url = config['DEFAULT']['BASE_URL_SB']
        key = config['DEFAULT']['CONSUMER_KEY_SB']
    else:
        base_url = config['DEFAULT']['BASE_URL']
        key = config['DEFAULT']['CONSUMER_KEY']

    # Get a new session, or use existing
    path = Path(picklefile)
    if path.is_file():
        with open(path, 'rb') as session_file:
            try:
                Session = pickle.load(session_file)
                _logger.info(f'{__name__}: Loaded existing session')
            except Exception as e:
                Session = None
            else:
                # Test session with a dummy call to get a quote and authorize if required
                url = f'{base_url}/v1/market/quote/aapl'
                if not _validate_session(Session, url):
                    Session = None

    if Session is None:
        Session = _authorize(callback)

    return Session


def _authorize(callback: Callable[[str], str]) -> OAuth1Session:
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

    # Construct callback URL to get auth code
    formated_auth_url = f'{authorize_url}?key={consumer_key}&token={token["oauth_token"]}'
    code = callback(formated_auth_url)

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


def _validate_session(session, url) -> bool:
    response = session.get(url)
    return (response is not None and response.status_code == 200)
