from sqlalchemy import Column, ForeignKey, Boolean, String, Integer, Float, Date
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from utils import utils as utils

Base = declarative_base()

class Exchange(Base):
    __tablename__ = 'exchange'
    id = Column(Integer, primary_key=True, autoincrement=True)
    abbreviation = Column('abbreviation', String(20), unique=True)
    name = Column('name', String(200), unique=True, nullable=False)
    securities = relationship('Security', back_populates='exchange')

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
    exchange = relationship('Exchange')
    company = relationship('Company', back_populates='security')
    pricing = relationship('Price', back_populates='security')
    index1 = relationship('Index', foreign_keys=[index1_id])
    index2 = relationship('Index', foreign_keys=[index2_id])
    index3 = relationship('Index', foreign_keys=[index3_id])

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
    description = Column('description', String(5000))
    url = Column('url', String(250))
    sector = Column('sector', String(200))
    industry = Column('industry', String(200))
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    security = relationship('Security', back_populates='company')

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
    security = relationship('Security')

    def __repr__(self):
        return f'<Price Model ({self.security_id})>'

    def __str__(self):
        return f'{self.date}: {self.security_id}'

class Incomplete(Base):
    __tablename__ = 'incomplete'
    id = Column(Integer, primary_key=True, autoincrement=True)
    security_id = Column(Integer, ForeignKey('security.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    security = relationship('Security')

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
