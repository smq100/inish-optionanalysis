from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import utils as u
from data import manager as m
from data import models as o


def is_symbol_valid(symbol):
    engine = create_engine(f'sqlite:///{m.SQLITE_DATABASE_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    e = session.query(o.Security).filter(o.Security.ticker==symbol.upper()).first()
    session.close()

    return (e is not None)

if __name__ == '__main__':
    from logging import DEBUG
    logger = u.get_logger(DEBUG)

    print(is_symbol_valid('AEXX'))
