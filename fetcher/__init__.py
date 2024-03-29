THROTTLE_FETCH = 0.05  # Min secs between calls to fetch pricing
THROTTLE_ERROR = 1.00  # Min secs between calls after error
RETRIES = 2            # Number of fetch retries after error


RATINGS = {
    'strongsell': 5,
    'sell': 5,
    'weaksell': 4,
    'negative': 4,
    'tradingsell': 4,
    'belowaverage': 4,
    'underperform': 4,
    'marketunderperform': 4,
    'sectorunderperform': 4,
    'weakbuy': 4,
    'reduce': 4,
    'underweight': 4,
    'underperformer': 3,
    'hold': 3,
    'neutral': 3,
    'perform': 3,
    'mixed': 3,
    'inline': 3,
    'sectorweight': 3,
    'fairvalue': 3,
    ' ': 3,
    'notrated': 3,
    'peerperform': 3,
    'equalweight': 3,
    'overperform': 2,
    'outperform': 2,
    'marketoutperform': 2,
    'sectoroutperform': 2,
    'outperformer': 2,
    'convictionbuy': 2,
    'sectorperformer': 2,
    'longtermbuy': 2,
    'positive': 2,
    'aboveaverage': 2,
    'graduallyaccumulate': 2,
    'overweight': 2,
    'overperformer': 3,
    'sectorperform': 2,
    'marketperform': 2,
    'speculativebuy': 2,
    'positive': 2,
    'accumulate': 2,
    'add': 2,
    'buy': 1,
    'toppick': 1,
    'strongbuy': 1,
}
