import json

import etrade.auth.auth as auth
from utils import logger

_logger = logger.get_logger()


class Alerts:
    def __init__(self, session):
        if not auth.base_url:
            raise AssertionError('Etrade session not initialized')

        self.session = session

    def alerts(self) -> tuple[str, list[dict]]:
        message = 'success'
        params = {'status': ['READ', 'UNREAD']}
        url = f'{auth.base_url}/v1/user/alerts.json'
        alert_data = []

        response = self.session.get(url, params=params)
        if response is not None and response.status_code == 200:
            alert_data = json.loads(response.text)
            parsed = json.dumps(alert_data, indent=2, sort_keys=True)
            _logger.debug(f'{__name__}: {parsed}')

            if alert_data is not None and 'AlertsResponse' in alert_data and 'Alert' in alert_data['AlertsResponse']:
                pass
            else:
                message = 'No alerts'
        elif response is not None and response.status_code == 204:
            alert_data = []
            message = 'No alerts'
        else:
            alert_data = []
            message = f'E*TRADE API service error: {response}'
            _logger.debug(f'{__name__}: Response Body: {response}')

        return message, alert_data
