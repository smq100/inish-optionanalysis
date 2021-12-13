import json

from utils import ui

_logger = ui.get_logger()


class Alerts:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def alerts(self):
        message = 'success'
        params = {'status': ['READ', 'UNREAD']}
        url = f'{self.base_url}/v1/user/alerts.json'
        alert_data = []

        response = self.session.get(url, params=params)
        if response is not None and response.status_code == 200:
            alert_data = json.loads(response.text)
            parsed = json.dumps(alert_data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if alert_data is not None and 'AlertsResponse' in alert_data and 'Alert' in alert_data['AlertsResponse']:
                pass
            else:
                message = 'None'
        elif response is not None and response.status_code == 204:
            alert_data = []
            message = 'None'
        else:
            alert_data = []
            message = f'E*TRADE API service error: {response}'
            _logger.debug(f'Response Body: {response}')

        return message, alert_data
