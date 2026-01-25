"""
Advanced Scraper - Unified Betting Engine
=========================================

Usa ScraperFC per ottenere dati xG da Understat.
"""

import ScraperFC as sfc
import time
import random
import pandas as pd
from datetime import datetime
from ..core.db_manager import DatabaseManager, AdvancedStat, Match

class AdvancedScraper:
    LEAGUE_MAP = {
        'Serie A': 'Serie A',
        'Premier League': 'EPL',
        'La Liga': 'La Liga',
        'Bundesliga': 'Bundesliga',
        'Ligue 1': 'Ligue 1'
    }

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.understat = sfc.Understat()

    def scrape_season(self, league_name: str, year: int):
        us_league = self.LEAGUE_MAP.get(league_name)
        if not us_league: return None
        
        try:
            df = self.understat.scrape_matches(year=year, league=us_league)
            time.sleep(random.uniform(1, 3))
            return df
        except: return None

    def save_stats(self, df, league_name: str, season_str: str):
        if df is None or df.empty: return
        session = self.db.get_session()
        added = 0
        for _, row in df.iterrows():
            try:
                date_str = str(row['Date'])[:10]
                m_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Cerchiamo il match
                match = session.query(Match).filter(
                    Match.league == league_name,
                    Match.season == season_str,
                    Match.date >= m_date.replace(hour=0, minute=0),
                    Match.date <= m_date.replace(hour=23, minute=59)
                ).first()
                
                if match:
                    stat = session.query(AdvancedStat).filter_by(match_id=match.id).first()
                    if not stat: stat = AdvancedStat(match_id=match.id)
                    
                    stat.home_xg = float(row['Home xG'])
                    stat.away_xg = float(row['Away xG'])
                    stat.source = 'Understat'
                    session.add(stat)
                    added += 1
            except: continue
        session.commit()
        session.close()
        print(f"   ✓ Stats {league_name}: {added} record aggiornati.")
