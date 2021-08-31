import pandas as pd

from utils import utils as utils


_logger = utils.get_logger()

VALID_TECHNICALS = ('high', 'low', 'close', 'volume', 'sma', 'rsi', 'beta', 'rating', 'value', 'true', 'false')
VALID_CONDITIONALS = ('le', 'eq', 'ge')
VALID_SERIES = ('min', 'max', 'none')


class Interpreter:
    def __init__(self, company:str, filter:dict):
        self.company = company
        self.filter = filter
        self.note = ''
        self.base = None
        self.base_technical = ''
        self.base_length = 0.0
        self.base_start = -1
        self.base_stop = 0
        self.base_series = 'none'
        self.base_factor = 1.0
        self.criteria = None
        self.criteria_conditional = ''
        self.criteria_value = 0.0
        self.criteria_technical = ''
        self.criteria_length = 0.0
        self.criteria_start = -1
        self.criteria_stop = 0
        self.criteria_series = 'none'
        self.criteria_factor = 0.0
        self.success = False
        self.score = 1.0
        self.result = ''

    def run(self) -> bool:
        if self.filter['base']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "base technical" specified in script')
        if self.filter['base']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "base series" specified in script')
        if self.filter['criteria']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "criteria technical" specified in script')
        if self.filter['criteria']['conditional'] not in VALID_CONDITIONALS:
            raise SyntaxError('Invalid "criteria test" specified in script')
        if self.filter['criteria']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "criteria series" specified in script')

        self.note = self.filter['note']
        self.base_technical = self.filter['base']['technical']
        self.base_length = self.filter['base']['length']
        self.base_start = self.filter['base']['start']
        self.base_stop = self.filter['base']['stop']
        self.base_series = self.filter['base']['series']
        self.base_factor = self.filter['base']['factor']
        self.criteria_conditional = self.filter['criteria']['conditional']
        self.criteria_value = self.filter['criteria']['value']
        self.criteria_technical = self.filter['criteria']['technical']
        self.criteria_length = self.filter['criteria']['length']
        self.criteria_start = self.filter['criteria']['start']
        self.criteria_stop = self.filter['criteria']['stop']
        self.criteria_series = self.filter['criteria']['series']
        self.criteria_factor = self.filter['criteria']['factor']

        (self.success, self.score) = self._calculate()

        return self.success

    def _calculate(self) -> bool:
        calculate = True
        success = False

        # Base value
        if self.base_technical == VALID_TECHNICALS[2]: # close
            self.base = self._get_base_close()
        elif self.base_technical == VALID_TECHNICALS[3]: # volume
            self.base = self._get_base_volume()
        elif self.base_technical == VALID_TECHNICALS[4]: # sma
            self.base = self._get_base_sma()
        elif self.base_technical == VALID_TECHNICALS[5]: # rsi
            self.base = self._get_base_rsi()
        elif self.base_technical == VALID_TECHNICALS[6]: # beta
            self.base = self._get_base_beta()
        elif self.base_technical == VALID_TECHNICALS[7]: # rating
            self.base = self._get_base_rating()
        elif self.base_technical == VALID_TECHNICALS[9]: # true
            calculate = False
            success = True
        elif self.base_technical == VALID_TECHNICALS[10]: # false
            calculate = False
            success = False
        else:
            raise SyntaxError('Invalid "base technical" specified in screen file')

        # Criteria value
        if not calculate:
            pass
        elif self.criteria_technical == VALID_TECHNICALS[8]: # value
            self.value = self._get_value()
        elif self.criteria_technical == VALID_TECHNICALS[0]: # high
            self.value = self._get_value_high()
        elif self.criteria_technical == VALID_TECHNICALS[1]: # low
            self.value = self._get_value_low()
        elif self.criteria_technical == VALID_TECHNICALS[2]: # close
            self.value = self._get_value_close()
        elif self.criteria_technical == VALID_TECHNICALS[3]: # volume
            self.value = self._get_value_volume()
        elif self.criteria_technical == VALID_TECHNICALS[4]: # sma
            self.value = self._get_value_sma()
        else:
            raise SyntaxError('Invalid "criteria technical" specified in screen file')

        return self._compare() if calculate else (success, 1.0)

    def _compare(self) -> bool:
        self.success = False
        self.score = 1.0

        if not self.base.empty:
            base = self.base.iloc[-1] * self.base_factor
            value = 0.0

            if self.criteria_conditional == VALID_CONDITIONALS[0]: # le
                if self.criteria_series == VALID_SERIES[2]: # na
                    if len(self.value) > 0:
                        value = self.value.iloc[-1] * self.criteria_factor
                        self.score = value / base
                        if base <= value:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[0]: # min
                    if len(self.value) > 0:
                        value = self.value.min() * self.criteria_factor
                        self.score = value / base
                        if base <= value:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[1]: # max
                    if len(self.value) > 0:
                        value = self.value.max() * self.criteria_factor
                        self.score = value / base
                        if base <= value:
                            self.success = True

            elif self.criteria_conditional == VALID_CONDITIONALS[1]: # eq
                if len(self.value) > 0:
                    value = self.value.min() * self.criteria_factor
                    if base == value:
                        self.success = True

            elif self.criteria_conditional == VALID_CONDITIONALS[2]: # ge
                if self.criteria_series == VALID_SERIES[2]: # na
                    if len(self.value) > 0:
                        value = self.value.iloc[-1] * self.criteria_factor
                        self.score = base / value
                        if base >= value:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[0]: # min
                    if len(self.value) > 0:
                        value = self.value.min() * self.criteria_factor
                        self.score = base / value
                        if base >= value:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[1]: # max
                    if len(self.value) > 0:
                        value = self.value.max() * self.criteria_factor
                        self.score = base / value
                        if base >= value:
                            self.success = True

            self.result = f'{self.company.ticker:6s}{str(self.success)[:1]}: {self.score:.2f}: {self.note} ' + \
                f'{self.base_technical}({self.base_length})/{base:.2f}*{self.base_factor:.2f} ' + \
                f'{self.criteria_conditional} ' + \
                f'{self.criteria_technical}({self.criteria_length})/{self.criteria_start}/{self.criteria_series}/{value:.2f}*{self.criteria_factor:.2f}'

            _logger.info(self.result)
        else:
            _logger.warning(f'{__name__}: No technical information for {self.company}')

        return (self.success, self.score)

    def _get_base_close(self) -> pd.Series:
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        return self.company.get_close()[sl]

    def _get_base_volume(self) -> pd.Series:
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        return self.company.get_volume()[sl]

    def _get_base_sma(self) -> pd.Series:
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        return self.company.ta.calc_sma(self.base_length)[sl]

    def _get_base_rsi(self) -> pd.Series:
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        return self.company.ta.calc_rsi()[sl]

    def _get_base_beta(self) -> pd.Series:
        beta = self.company.get_beta()
        return pd.Series(beta)

    def _get_base_rating(self) -> pd.Series:
        rating = self.company.get_rating()
        return pd.Series(rating)

    def _get_value(self) -> pd.Series:
        value = self.criteria_value
        return pd.Series([value])

    def _get_value_high(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_high()[sl]

    def _get_value_low(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_low()[sl]

    def _get_value_close(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_close()[sl]

    def _get_value_volume(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_volume()[sl]

    def _get_value_sma(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.ta.calc_sma(self.criteria_length)[sl]
