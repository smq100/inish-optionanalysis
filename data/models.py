from sqlalchemy import Column, ForeignKey, Boolean, String, Integer, BigInteger, Float, Date
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from utils import ui

Base = declarative_base()

class Exchange(Base):
    __tablename__ = 'exchange'
    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column('abbreviation', String(20), unique=True)
    name = Column('name', String(200), unique=True, nullable=False)

    securities = relationship('Security', backref='exchange', passive_deletes=True)

    def __init__(self, abbreviation, name):
        self.abbreviation = abbreviation.upper()
        self.name = name

    def __repr__(self):
        return f'<Exchange Model ({self.acronym})>'

    def __str__(self):
        return self.abbreviation

class Security(Base):
    __tablename__ = 'security'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column('ticker', String(12), nullable=False, unique=True)
    active = Column('active', Boolean, default=True)
    exchange_id = Column(Integer, ForeignKey('exchange.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    index1_id = Column(Integer, ForeignKey('index.id', onupdate='CASCADE', ondelete='SET NULL'))
    index2_id = Column(Integer, ForeignKey('index.id', onupdate='CASCADE', ondelete='SET NULL'))
    index3_id = Column(Integer, ForeignKey('index.id', onupdate='CASCADE', ondelete='SET NULL'))

    pricing = relationship('Price', backref='security', passive_deletes=True)
    company = relationship('Company', backref='security', passive_deletes=True)
    incomplete = relationship('Incomplete', backref='security', passive_deletes=True)

    index1 = relationship('Index', foreign_keys=index1_id, backref='index1', passive_deletes=True)
    index2 = relationship('Index', foreign_keys=index2_id, backref='index2', passive_deletes=True)
    index3 = relationship('Index', foreign_keys=index3_id, backref='index3', passive_deletes=True)

    def __init__(self, ticker):
        self.ticker = ticker.upper()

    def __repr__(self):
        return f'<Security Model ({self.ticker})>'

    def __str__(self):
        return self.ticker

class Index(Base):
    __tablename__ = 'index'
    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column('abbreviation', String(20), unique=True)
    name = Column('name', String(200), nullable=False)

    # index1 = relationship('Security', foreign_keys=[Security.index1_id], backref='index')

    def __init__(self, abbreviation, name):
        self.abbreviation = abbreviation.upper()
        self.name = name

    def __repr__(self):
        return f'<Index Model({self.name})>'

    def __str__(self):
        return self.abbreviation

class Company(Base):
    __tablename__ = 'company'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), nullable=False)
    description = Column('description', String(5000), nullable=False, default='')
    url = Column('url', String(250), nullable=False, default='')
    sector = Column('sector', String(200), nullable=False, default='')
    industry = Column('industry', String(200), nullable=False, default='')
    beta = Column('beta', Float, nullable=False, default=1.0)
    marketcap = Column('marketcap', BigInteger, nullable=False, default=0)
    rating = Column('rating', Float, nullable=False, default=3.0)
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return f'<Company Model ({self.name})>'

    def __str__(self):
        return self.name

class Price(Base):
    __tablename__ = 'price'
    __table_args__ = (UniqueConstraint('date', 'security_id', name='date_id_uc'), )
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column('date', Date, nullable=False)
    open = Column('open', Float)
    high = Column('high', Float)
    low = Column('low', Float)
    close = Column('close', Float)
    volume = Column('volume', Float)
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return f'<Price Model ({self.security_id})>'

    def __str__(self):
        return f'{self.date}: {self.security_id}'

class Incomplete(Base):
    __tablename__ = 'incomplete'
    id = Column(Integer, primary_key=True, autoincrement=True)
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return '<Incomplete Model>'

# class Adjustment(Base):
#     __tablename__ = 'adjustment'
#     id = Column(Integer, primary_key=True)
#     date = Column('date', Date, nullable=False)
#     factor = Column('factor', Float, nullable=False)
#     dividend = Column('dividend', Float)
#     split_ratio = Column('split_ratio', Float)
#     security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
#     security = relationship('Security')
