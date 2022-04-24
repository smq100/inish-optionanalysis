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

    def alerts(self) -> pd.DataFrame:
        self.message = 'success'
        params = {'status': ['READ', 'UNREAD']}
        url = f'{auth.base_url}{URL_ALERTS}'
        alert_data = []

        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            alert_data = response.json()
            if alert_data is not None and 'AlertsResponse' in alert_data and 'Alert' in alert_data['AlertsResponse']:
                parsed = json.dumps(alert_data, indent=2, sort_keys=True)
                _logger.debug(f'{__name__}: {parsed}')
            else:
                self.message = 'E*TRADE API service error'
        elif response is not None and response.status_code == 204:
            self.message = 'No alerts'
        else:
            _logger.debug(f'{__name__}: Response Body: {response}')
            self.message = f'E*TRADE API service error: {response}'

        alert_table = pd.DataFrame()
        if self.message == 'success':
            data = alert_data['AlertsResponse']['Alert']
            alert_table = pd.DataFrame.from_dict(data)

        return alert_table

'''
Sample AlertsResponse

{
  "AlertsResponse": {
    "Alert": [
      {
        "createTime": 1328115640,
        "id": 1099,
        "status": "READ",
        "subject": "Bank Statement Available for Jan'12"
      },
      {
          ...
      }
'''