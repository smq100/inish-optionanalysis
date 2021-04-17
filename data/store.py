import datetime as dt

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
import pandas as pd

from utils import utils as u
import data as d
from data import models as o

logger = u.get_logger()


def is_symbol_valid(symbol):
    engine = create_engine(d.SQLITE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        e = session.query(o.Security).filter(o.Security.ticker==symbol.upper()).first()

    return (e is not None)

def is_exchange(exchange):
    ret = False
    for e in d.EXCHANGES:
        if exchange == e['abbreviation']:
            ret = True
            break
    return ret

def is_index(index):
    ret = False
    for i in d.INDEXES:
        if index == i['abbreviation']:
            ret = True
            break
    return ret

def get_history(ticker, days):
    results = pd.DataFrame
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        t = session.query(o.Security).filter(o.Security.ticker==ticker.upper()).first()
        if t is not None:
            if days < 0:
                p = session.query(o.Price).filter(o.Price.security_id==t.id)
                results = pd.read_sql(p.statement, engine)
                logger.info(f'{__name__}: Fetched entire price history for {ticker}')
            elif days > 1:
                start = dt.datetime.today() - dt.timedelta(days=days)
                p = session.query(o.Price).filter(and_(o.Price.security_id==t.id, o.Price.date >= start))
                results = pd.read_sql(p.statement, engine)
                logger.info(f'{__name__}: Fetched {days} days of price history for {ticker}')
        else:
            logger.warning(f'{__name__}: No history found for {ticker}')

    return results

def get_exchange(exchange):
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        exc = session.query(o.Exchange).filter(o.Exchange.abbreviation==exchange.upper()).first()
        if exc is not None:
            t = session.query(o.Security).filter(o.Security.exchange_id==exc.id).all()
            for symbol in t:
                results += [symbol.ticker]
        else:
            raise ValueError(f'Invalid exchange: {exchange}')

    return results

def get_index(index):
    results = []
    engine = create_engine(d.ACTIVE_URI, echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        i = session.query(o.Index).filter(o.Index.abbreviation==index.upper()).first()
        if i is not None:
            t = session.query(o.Security).filter(or_(o.Security.index1_id==i.id, o.Security.index2_id==i.id)).all()
            for symbol in t:
                results += [symbol.ticker]
        else:
            raise ValueError(f'Invalid index: {index}')

    return results


if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    p = get_index('DOW')
    print(p)
    # print(is_symbol_valid('IBM'))
