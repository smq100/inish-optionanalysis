import pandas as pd

from analysis.company import Company
from utils import logger

_logger = logger.get_logger()

VALID_TECHNICALS = ('high', 'low', 'close', 'volume', 'sma', 'rsi', 'beta', 'rating', 'mcap', 'value', 'true')
VALID_CONDITIONALS = ('le', 'eq', 'ge')
VALID_SERIES = ('min', 'max', 'none')


class Interpreter:
    def __init__(self, company: Company, filter: dict):
        self.company = company
        self.filter = filter
        self.note = ''
        self.weight = 1.0
        self.base = pd.Series(dtype=float)
        self.base_technical = ''
        self.base_length = 0.0
        self.base_start = -1
        self.base_stop = 0
        self.base_series = 'none'
        self.base_factor = 1.0
        self.conditional = ''
        self.criteria = pd.Series(dtype=float)
        self.criteria_value = 0.0
        self.criteria_technical = ''
        self.criteria_length = 0.0
        self.criteria_start = -1
        self.criteria_stop = 0
        self.criteria_series = 'none'
        self.criteria_factor = 0.0

        self.success = False
        self.score = 1.0
        self.description = ''

    def __str__(self):
        return self.description

    def run(self) -> bool:
        if self.filter['base']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "base technical" specified in script')
        if self.filter['base']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "base series" specified in script')
        if self.filter['conditional'] not in VALID_CONDITIONALS:
            raise SyntaxError('Invalid "conditional" specified in script')
        if self.filter['criteria']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "criteria technical" specified in script')
        if self.filter['criteria']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "criteria series" specified in script')

        self.note = self.filter['note']
        self.weight = self.filter.get('weight', 1.0)
        self.base_technical = self.filter['base']['technical']
        self.base_length = self.filter['base']['length']
        self.base_start = self.filter['base']['start']
        self.base_stop = self.filter['base']['stop']
        self.base_series = self.filter['base']['series']
        self.base_factor = self.filter['base']['factor']
        self.conditional = self.filter['conditional']
        self.criteria_value = self.filter['criteria']['value']
        self.criteria_technical = self.filter['criteria']['technical']
        self.criteria_length = self.filter['criteria']['length']
        self.criteria_start = self.filter['criteria']['start']
        self.criteria_stop = self.filter['criteria']['stop']
        self.criteria_series = self.filter['criteria']['series']
        self.criteria_factor = self.filter['criteria']['factor']

        (self.success, self.score) = self._calculate()

        return self.success

    def _calculate(self) -> tuple:
        self.base = pd.Series(dtype=float)
        calculate = True

        # Base value
        if self.base_technical == VALID_TECHNICALS[2]:   # close
            value = self._get_base_close()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[3]:  # volume
            value = self._get_base_volume()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[4]:  # sma
            value = self._get_base_sma()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[5]:  # rsi
            value = self._get_base_rsi()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[6]:  # beta
            value = self._get_base_beta()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[7]:  # rating
            value = self._get_base_rating()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[8]:  # mcap
            value = self._get_base_mcap()
            if not value.empty:
                self.base = value

        elif self.base_technical == VALID_TECHNICALS[10]:  # true
            calculate = False

        else:
            raise SyntaxError('Invalid "base technical" specified in screen file')

        # Criteria value
        if calculate:
            if self.criteria_technical == VALID_TECHNICALS[9]:  # value
                self.criteria = self._get_criteria()
            elif self.criteria_technical == VALID_TECHNICALS[0]:  # high
                self.criteria = self._get_criteria_high()
            elif self.criteria_technical == VALID_TECHNICALS[1]:  # low
                self.criteria = self._get_criteria_low()
            elif self.criteria_technical == VALID_TECHNICALS[2]:  # close
                self.criteria = self._get_criteria_close()
            elif self.criteria_technical == VALID_TECHNICALS[3]:  # volume
                self.criteria = self._get_criteria_volume()
            elif self.criteria_technical == VALID_TECHNICALS[4]:  # sma
                self.criteria = self._get_criteria_sma()
            else:
                raise SyntaxError('Invalid "criteria technical" specified in screen file')

        return self._compare() if calculate else (True, 1.0)

    def _compare(self) -> tuple:
        self.success = False
        self.score = 1.0

        if not self.base.empty:
            base = self.base.iloc[-1] * self.base_factor
            criteria = 0.0

            if self.conditional == VALID_CONDITIONALS[0]:  # le
                if self.criteria_series == VALID_SERIES[2]:  # na
                    if self.criteria.size > 0:
                        criteria = self.criteria.iloc[-1] * self.criteria_factor
                        self.score = criteria / base if base > 0 else 1.0
                        if base <= criteria:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[0]:  # min
                    if self.criteria.size > 0:
                        criteria = self.criteria.min() * self.criteria_factor
                        self.score = criteria / base if base > 0 else 1.0
                        if base <= criteria:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[1]:  # max
                    if self.criteria.size > 0:
                        criteria = self.criteria.max() * self.criteria_factor
                        self.score = criteria / base if base > 0 else 1.0
                        if base <= criteria:
                            self.success = True

            elif self.conditional == VALID_CONDITIONALS[1]:  # eq
                if self.criteria.size > 0:
                    criteria = self.criteria.min() * self.criteria_factor
                    if base == criteria:
                        self.success = True

            elif self.conditional == VALID_CONDITIONALS[2]:  # ge
                if self.criteria_series == VALID_SERIES[2]:  # na
                    if self.criteria.size > 0:
                        criteria = self.criteria.iloc[-1] * self.criteria_factor
                        self.score = base / criteria if criteria > 0 else 1.0
                        if base >= criteria:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[0]:  # min
                    if self.criteria.size > 0:
                        criteria = self.criteria.min() * self.criteria_factor
                        self.score = base / criteria if criteria > 0 else 1.0
                        if base >= criteria:
                            self.success = True
                elif self.criteria_series == VALID_SERIES[1]:  # max
                    if self.criteria.size > 0:
                        criteria = self.criteria.max() * self.criteria_factor
                        self.score = base / criteria if criteria > 0 else 1.0
                        if base >= criteria:
                            self.success = True

            self.score = self.score * self.weight if self.weight > 0.0 else 1.0

            basef = f'{base:.2f}' if base < 1e5 else f'{base:.1e}'
            criteriaf = f'{criteria:.2f}' if criteria < 1e5 else f'{criteria:.1e}'
            pf = 'Pass' if self.success else 'Fail'
            self.description = \
                f'{self.company.ticker:6s} {pf} {self.score:6.2f}: {self.note:18s}: ' + \
                f'{self.base_technical}({self.base_length})/{basef}@{self.base_factor:.2f} ' + \
                f'{self.conditional} ' + \
                f'{self.criteria_technical}({self.criteria_length})/{self.criteria_start}/{self.criteria_series}/{criteriaf}@{self.criteria_factor:.2f} ' + \
                f'w={self.weight:.1f}'
        else:
            _logger.info(f'{__name__}: No technical information for {self.company}')

            pf = 'Pass' if self.success else 'Fail'
            self.description = \
                f'{self.company.ticker:6s} {pf} {self.score:6.2f}: {self.note:18s}: ' + \
                f'{self.base_technical}({self.base_length})/***@{self.base_factor:.2f} ' + \
                f'{self.conditional} ' + \
                f'{self.criteria_technical}({self.criteria_length})/{self.criteria_start}/{self.criteria_series}/***@{self.criteria_factor:.2f} ' + \
                f'w={self.weight:.1f}'

        _logger.info(self.description)

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
        value = pd.Series(dtype=float)
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        if self.company.ta is not None:
            value = self.company.ta.calc_sma(int(self.base_length))[sl]
        return value

    def _get_base_rsi(self) -> pd.Series:
        value = pd.Series(dtype=float)
        start = None if self.base_start == 0 else self.base_start
        stop = None if self.base_stop == 0 else self.base_stop
        sl = slice(start, stop)
        if self.company.ta is not None:
            value = self.company.ta.calc_rsi(int(self.base_length))[sl]
        return value

    def _get_base_beta(self) -> pd.Series:
        beta = self.company.get_beta()
        return pd.Series(beta)

    def _get_base_rating(self) -> pd.Series:
        rating = self.company.get_rating()
        return pd.Series(rating)

    def _get_base_mcap(self) -> pd.Series:
        rating = float(self.company.get_marketcap())
        return pd.Series(rating)

    def _get_criteria(self) -> pd.Series:
        value = self.criteria_value
        return pd.Series([value])

    def _get_criteria_high(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_high()[sl]

    def _get_criteria_low(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_low()[sl]

    def _get_criteria_close(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_close()[sl]

    def _get_criteria_volume(self) -> pd.Series:
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        return self.company.get_volume()[sl]

    def _get_criteria_sma(self) -> pd.Series:
        value = pd.Series(dtype=float)
        start = None if self.criteria_start == 0 else self.criteria_start
        stop = None if self.criteria_stop == 0 else self.criteria_stop
        sl = slice(start, stop)
        if self.company.ta is not None:
            value = self.company.ta.calc_sma(int(self.criteria_length))[sl]
        return value
