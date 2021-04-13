import datetime as dt

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import pandas as pd

from utils import utils as u
from data import models as o
from data import SQLITE_DATABASE_PATH


def is_symbol_valid(symbol):
    engine = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}', echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        e = session.query(o.Security).filter(o.Security.ticker==symbol.upper()).first()

    return (e is not None)

def get_history(ticker, days):
    results = pd.DataFrame
    engine = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}', echo=False)
    session = sessionmaker(bind=engine)

    with session() as session:
        t = session.query(o.Security).filter(o.Security.ticker==ticker.upper()).first()
        if t is not None:
            if days < 0:
                q = session.query(o.Price).filter(o.Price.security_id==t.id)
                results = pd.read_sql(q.statement, engine)
            elif days > 1:
                start = dt.datetime.today() - dt.timedelta(days=days)
                q = session.query(o.Price).filter(and_(o.Price.security_id==t.id, o.Price.date >= start))
                results = pd.read_sql(q.statement, engine)

    return results

if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    p = get_history('IBM', -1)
    print(p['close'])
    # print(is_symbol_valid('IBM'))
