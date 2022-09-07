from enum import Enum


class StrategyType(Enum):
    Call = 'call'
    Put = 'put'
    Vertical = 'vertical'
    IronCondor = 'iron condor'
    IronButterfly = 'iron butterfly'

    @staticmethod
    def from_str(label: str):
        if 'call' in label.lower():
            return StrategyType.Call
        elif 'put' in label.lower():
            return StrategyType.Put
        elif 'vert' in label.lower():
            return StrategyType.Vertical
        elif 'condor' in label.lower():
            return StrategyType.IronCondor
        elif 'butterfly' in label.lower():
            return StrategyType.IronButterfly
        elif 'ic' in label.lower():
            return StrategyType.IronCondor
        elif 'ib' in label.lower():
            return StrategyType.IronButterfly
        else:
            raise ValueError('Invalid Strategy type')


class ProductType(Enum):
    Call = 'call'
    Put = 'put'
    Hybrid = 'hybrid'

    @staticmethod
    def from_str(label: str):
        if 'call' in label.lower():
            return ProductType.Call
        elif 'put' in label.lower():
            return ProductType.Put
        elif 'hybrid' in label.lower():
            return ProductType.Hybrid
        else:
            raise ValueError('Invalid Product type')


class DirectionType(Enum):
    Long = 'long'
    Short = 'short'

    @staticmethod
    def from_str(label: str):
        if 'long' in label.lower():
            return DirectionType.Long
        elif 'short' in label.lower():
            return DirectionType.Short
        else:
            raise ValueError('Invalid Direction type')


class OutlayType(Enum):
    Debit = 'debit'
    Credit = 'credit'


class SentimentType(Enum):
    Bullish = 'bullish'
    Bearish = 'bearish'
    LowVolatility = 'low volatility'
    HighVolatility = 'high volatility'
