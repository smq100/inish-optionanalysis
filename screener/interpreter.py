import datetime

import pandas as pd

from utils import utils as u


logger = u.get_logger()

VALID_TECHNICALS = ('close', 'sma', 'none')
VALID_CONDITIONALS = ('lt', 'eq', 'gt')
VALID_SERIES = ('min', 'max', 'na')

class SyntaxError(Exception):
    def __init__(self, message):
        super().__init__(message)


class Interpreter:
    def __init__(self, symbol, filter):
        self.symbol = symbol
        self.filter = filter
        self.base = None
        self.base_technical = ''
        self.base_length = 0.0
        self.base_start = -1
        self.base_stop = 0
        self.base_series = 'na'
        self.base_factor = 1.0
        self.criteria = None
        self.criteria_conditional = ''
        self.criteria_value = 0.0
        self.criteria_technical = ''
        self.criteria_length = 0.0
        self.criteria_start = -1
        self.criteria_stop = 0
        self.criteria_series = 'na'
        self.criteria_factor = 0.0
        self.result = False

    def run(self):
        result = False
        if self.filter['base']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "technical" specified in script')
        if self.filter['base']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "series" specified in script')
        if self.filter['criteria']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "technical" specified in script')
        if self.filter['criteria']['conditional'] not in VALID_CONDITIONALS:
            raise SyntaxError('Invalid "test" specified in script')
        if self.filter['criteria']['series'] not in VALID_SERIES:
            raise SyntaxError('Invalid "series" specified in script')

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

        result = self._calculate()

        return result

    def _calculate(self):
        ### Close
        if self.base_technical == VALID_TECHNICALS[0]:
            # base value
            start = None if self.base_start == 0 else self.base_start
            stop = None if self.base_stop == 0 else self.base_stop
            sl = slice(start, stop, None)
            self.base = self.symbol.ta.get_close()[sl] * self.base_factor

            # Criteria
            if self.criteria_technical == VALID_TECHNICALS[-1]: # none
                value = self.criteria_value * self.criteria_factor
                self.value = pd.Series([value])
            elif self.criteria_technical == VALID_TECHNICALS[1]: #sma
                start = None if self.criteria_start == 0 else self.criteria_start
                stop = None if self.criteria_stop == 0 else self.criteria_stop
                sl = slice(start, stop, None)
                self.value = self.symbol.ta.calc_sma(self.criteria_length)[sl] * self.criteria_factor

        return self._calc_comparison()

    def _calc_comparison(self):
        result = False
        base = self.base.iloc[-1]

        if self.criteria_conditional == VALID_CONDITIONALS[0]: # lt
            if self.criteria_series == VALID_SERIES[-1]: # na
                value = self.value.iloc[-1]
                if base < value:
                    result = True
            elif self.criteria_series == VALID_SERIES[0]: # min
                value = self.value.min()
                if base < value.min():
                    result = True
            elif self.criteria_series == VALID_SERIES[1]: # max
                value = self.value.max()
                if base < value:
                    result = True

        elif self.criteria_conditional == VALID_CONDITIONALS[1]: # eq
            value = self.value.min()
            if base == value:
                result = True

        elif self.criteria_conditional == VALID_CONDITIONALS[2]: # gt
            if self.criteria_series == VALID_SERIES[-1]: # na
                value = self.value.iloc[-1]
                if base > value:
                    result = True
            elif self.criteria_series == VALID_SERIES[0]: # min
                value = self.value.min()
                if base > value:
                    result = True
            elif self.criteria_series == VALID_SERIES[1]: # max
                value = self.value.max()
                if base > value:
                    result = True

        logger.debug(f'{__name__}: ' +
            f'{str(self.symbol):4s}:{str(result):5s} ' +
            f'{self.base_technical}/{base:6.2f} ' +
            f'{self.criteria_conditional} ' +
            f'{self.criteria_technical}/{value:6.2f}')

        return result
