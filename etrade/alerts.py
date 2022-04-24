import json

import pandas as pd
from requests_oauthlib import OAuth1Session

import etrade.auth as auth
from utils import logger

_logger = logger.get_logger()


URL_ALERTS = '/v1/user/alerts.json'


class Alerts:
    def __init__(self, session):
        if not auth.base_url:
            raise AssertionError('Etrade session not initialized')

        self.session: OAuth1Session = session
        self.message = ''

    def alerts(self) -> tuple[str, list[dict]]:
        self.message = 'success'
        params = {'status': ['READ', 'UNREAD']}
        url = f'{auth.base_url}{URL_ALERTS}'
        alert_data = []

        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            alert_data = response.json()
            if alert_data is not None and 'AlertsResponse' in alert_data and 'Alert' in alert_data['AlertsResponse']:
                parsed = json.dumps(alert_data, indent=2, sort_keys=True)
                print(parsed)
                _logger.debug(f'{__name__}: {parsed}')
            else:
                self.message = 'E*TRADE API service error'
        elif response is not None and response.status_code == 400:
            _logger.debug(f'{__name__}: Response Body: {response}')
            alert_data = json.loads(response.text)
            self.message = f'\nError ({alert_data["Error"]["code"]}): {alert_data["Error"]["message"]}'
        else:
            _logger.debug(f'{__name__}: Response Body: {response}')
            self.message = 'E*TRADE API service error'

        return alert_data
