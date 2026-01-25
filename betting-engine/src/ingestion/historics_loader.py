"""
Historics Loader - Unified Betting Engine
=========================================

Scarica i CSV da football-data.co.uk e li inserisce nel DB.
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from ..core.db_manager import DatabaseManager, Match
from ..core.config import settings

class HistoricsLoader:
    BASE_URL = "https://www.football-data.co.uk/mmz4281/"
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.raw_dir = settings.RAW_CSV_DIR

    def download_season(self, league_code: str, season_str: str):
        url = f"{self.BASE_URL}{season_str}/{league_code}.csv"
        file_path = self.raw_dir / f"{league_code}_{season_str}.csv"
        
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        except Exception:
            return None

    def process_csv(self, file_path: Path, league_name: str, season_year: str):
        if not file_path or not file_path.exists():
            return
            
        try:
            df = pd.read_csv(file_path, on_bad_lines='skip')
        except:
            df = pd.read_csv(file_path, encoding='latin1', on_bad_lines='skip')

        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        
        col_map = {'Date': 'date', 'HomeTeam': 'home_team', 'AwayTeam': 'away_team', 
                   'FTHG': 'fthg', 'FTAG': 'ftag', 'FTR': 'ftr'}
        
        odds_cols = {'AvgH': 'avg_h', 'AvgD': 'avg_d', 'AvgA': 'avg_a',
                     'BbAvH': 'avg_h', 'BbAvD': 'avg_d', 'BbAvA': 'avg_a'}
        
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for old, new in odds_cols.items():
            if old in df.columns and new not in df.columns:
                df = df.rename(columns={old: new})

        def parse_date(x):
            for fmt in ('%d/%m/%y', '%d/%m/%Y', '%d/%m/%G'):
                try: return datetime.strptime(x, fmt)
                except: continue
            return None

        df['date'] = df['date'].apply(parse_date)
        df = df.dropna(subset=['date'])

        session = self.db.get_session()
        added = 0
        for _, row in df.iterrows():
            try:
                exists = session.query(Match).filter_by(
                    date=row['date'], home_team=row['home_team'], away_team=row['away_team']
                ).first()
                if not exists:
                    match = Match(
                        league=league_name, season=season_year, date=row['date'],
                        home_team=row['home_team'], away_team=row['away_team'],
                        fthg=int(row['fthg']), ftag=int(row['ftag']), ftr=row['ftr'],
                        avg_h=float(row['avg_h']) if 'avg_h' in row else None,
                        avg_d=float(row['avg_d']) if 'avg_d' in row else None,
                        avg_a=float(row['avg_a']) if 'avg_a' in row else None,
                    )
                    session.add(match)
                    added += 1
            except: continue
        
        session.commit()
        session.close()
        print(f"   ✓ {league_name} {season_year}: {added} nuove partite.")

    def backfill(self, leagues=None, years=range(15, 25)):
        leagues = leagues or settings.LEAGUES.keys()
        for year in years:
            season_str = f"{year}{year+1}"
            season_year = f"20{year}/20{year+1}"
            for l_name in leagues:
                l_code = settings.LEAGUES[l_name]['code']
                path = self.download_season(l_code, season_str)
                if path:
                    self.process_csv(path, l_name, season_year)
