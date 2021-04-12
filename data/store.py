from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

from utils import utils as u
from data import SQLITE_DATABASE_PATH
from data import models as o


engine = create_engine(f'sqlite:///{SQLITE_DATABASE_PATH}', echo=False)
session = sessionmaker(bind=engine)

def is_symbol_valid(symbol):
    global session
    with session() as session:
        e = session.query(o.Security).filter(o.Security.ticker==symbol.upper()).first()

    return (e is not None)

def get_pricing(ticker, days):
    global session
    results = pd.DataFrame

    with session() as session:
        t = session.query(o.Security).filter(o.Security.ticker==ticker.upper()).first()
        if t is not None:
            q = session.query(o.Price).filter(o.Price.security_id==t.id)
            results = pd.read_sql(q.statement, engine)

    return results

if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    # print(get_pricing('IBM', 100))
    print(is_symbol_valid('IBM'))
