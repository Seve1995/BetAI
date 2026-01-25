"""
Database Manager - Unified Betting Engine
=========================================

Gestisce lo schema SQLite e le operazioni di I/O usando SQLAlchemy.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

Base = declarative_base()

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    league = Column(String, nullable=False)
    season = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    fthg = Column(Integer)
    ftag = Column(Integer)
    ftr = Column(String)
    avg_h = Column(Float)
    avg_d = Column(Float)
    avg_a = Column(Float)
    source = Column(String, default='football-data.co.uk')
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('date', 'home_team', 'away_team', name='_match_uc'),)

class AdvancedStat(Base):
    __tablename__ = 'advanced_stats'
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), unique=True)
    home_xg = Column(Float)
    away_xg = Column(Float)
    home_shots = Column(Integer)
    away_shots = Column(Integer)
    source = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TeamMapping(Base):
    __tablename__ = 'team_mapping'
    id = Column(Integer, primary_key=True)
    standard_name = Column(String, nullable=False)
    alias = Column(String, nullable=False)
    provider = Column(String)

class DatabaseManager:
    def __init__(self, db_path=None):
        self.engine = create_engine(f'sqlite:///{db_path or settings.DB_PATH}')
        self.Session = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(self.engine)
        print("✓ Database Unified Inizializzato.")

    def get_session(self):
        return self.Session()
