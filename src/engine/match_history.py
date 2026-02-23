"""
MATCH HISTORY - SQLite database for match results & predictions
================================================================

Stores every match result and model prediction for:
- MLE parameter fitting (Dixon-Coles)
- Calibration analysis (Brier score, log-loss)
- CLV tracking (bet odds vs closing odds)

Schema:
    matches: id, date, league, home, away, home_goals, away_goals, status
    predictions: match_id, timestamps, predicted probabilities, odds
"""

import sqlite3
import os
from datetime import datetime


class MatchHistory:
    def __init__(self, db_path="data/match_history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                league TEXT NOT NULL,
                home TEXT NOT NULL,
                away TEXT NOT NULL,
                home_goals INTEGER,
                away_goals INTEGER,
                status TEXT DEFAULT 'scheduled',
                source TEXT DEFAULT 'fotmob',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, league, home, away)
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                pred_home_xg REAL,
                pred_away_xg REAL,
                pred_home_win REAL,
                pred_draw REAL,
                pred_away_win REAL,
                pred_over25 REAL,
                pred_btts REAL,
                bet_odds REAL,
                bet_market TEXT,
                closing_odds REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            );

            CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league);
            CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
            CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
        """)
        self.conn.commit()

    def insert_match(self, date: str, league: str, home: str, away: str,
                     home_goals: int = None, away_goals: int = None,
                     status: str = 'scheduled', source: str = 'fotmob') -> int:
        """Insert a match, returning its ID. Upserts if duplicate."""
        try:
            cur = self.conn.execute("""
                INSERT INTO matches (date, league, home, away, home_goals, away_goals, status, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, league, home, away) 
                DO UPDATE SET home_goals=excluded.home_goals, 
                              away_goals=excluded.away_goals,
                              status=excluded.status
            """, (date, league, home, away, home_goals, away_goals, status, source))
            self.conn.commit()
            return cur.lastrowid
        except Exception:
            self.conn.rollback()
            # Return existing match ID
            row = self.conn.execute(
                "SELECT id FROM matches WHERE date=? AND league=? AND home=? AND away=?",
                (date, league, home, away)
            ).fetchone()
            return row['id'] if row else -1

    def log_prediction(self, match_id: int, prediction: dict,
                       bet_odds: float = None, bet_market: str = None):
        """Log a model prediction for a match."""
        self.conn.execute("""
            INSERT INTO predictions (match_id, pred_home_xg, pred_away_xg,
                pred_home_win, pred_draw, pred_away_win, pred_over25, pred_btts,
                bet_odds, bet_market)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            prediction.get('home_xg'),
            prediction.get('away_xg'),
            prediction.get('home_win'),
            prediction.get('draw'),
            prediction.get('away_win'),
            prediction.get('over_25'),
            prediction.get('btts'),
            bet_odds,
            bet_market,
        ))
        self.conn.commit()

    def update_result(self, match_id: int, home_goals: int, away_goals: int):
        """Update match result."""
        self.conn.execute("""
            UPDATE matches SET home_goals=?, away_goals=?, status='finished'
            WHERE id=?
        """, (home_goals, away_goals, match_id))
        self.conn.commit()

    def get_training_data(self, league: str = None, min_date: str = None) -> list:
        """
        Get finished matches for model fitting.
        
        Returns list of dicts: {date, league, home, away, home_goals, away_goals}
        """
        query = "SELECT * FROM matches WHERE status='finished' AND home_goals IS NOT NULL"
        params = []
        
        if league:
            query += " AND league=?"
            params.append(league)
        if min_date:
            query += " AND date>=?"
            params.append(min_date)
        
        query += " ORDER BY date ASC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_predictions_with_results(self) -> list:
        """Get predictions alongside actual results for calibration."""
        rows = self.conn.execute("""
            SELECT p.*, m.home_goals, m.away_goals, m.league, m.home, m.away, m.date
            FROM predictions p
            JOIN matches m ON p.match_id = m.id
            WHERE m.status='finished' AND m.home_goals IS NOT NULL
            ORDER BY m.date ASC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_teams_in_league(self, league: str) -> list:
        """Get all unique team names in a league."""
        rows = self.conn.execute("""
            SELECT DISTINCT team FROM (
                SELECT home AS team FROM matches WHERE league=?
                UNION
                SELECT away AS team FROM matches WHERE league=?
            )
        """, (league, league)).fetchall()
        return [r['team'] for r in rows]

    def seed_from_fotmob(self, scraper, leagues: list) -> int:
        """
        Seed database with historical match results from FotMob fixtures.
        
        Returns number of matches inserted.
        """
        total = 0
        
        for league_name in leagues:
            league_id = scraper.LEAGUE_IDS.get(league_name)
            if not league_id:
                continue
            
            print(f"   Seeding {league_name} (ID={league_id})...")
            
            try:
                url = f"{scraper.BASE_URL}/leagues?id={league_id}"
                response = scraper.session.get(url)
                response.raise_for_status()
                data = response.json()
                
                fixtures = data.get('fixtures', {})
                all_matches = fixtures.get('allMatches', [])
                
                count = 0
                for match in all_matches:
                    status = match.get('status', {})
                    if not status.get('finished'):
                        continue
                    
                    score_str = status.get('scoreStr', '')
                    if not score_str or '-' not in score_str:
                        continue
                    
                    parts = score_str.split('-')
                    try:
                        home_goals = int(parts[0].strip())
                        away_goals = int(parts[1].strip())
                    except (ValueError, IndexError):
                        continue
                    
                    home = match.get('home', {}).get('shortName') or match.get('home', {}).get('name', '')
                    away = match.get('away', {}).get('shortName') or match.get('away', {}).get('name', '')
                    
                    # Extract date from UTC time
                    utc_time = status.get('utcTime', '')
                    date_str = utc_time[:10] if len(utc_time) >= 10 else ''
                    
                    if home and away and date_str:
                        self.insert_match(
                            date=date_str,
                            league=league_name,
                            home=home,
                            away=away,
                            home_goals=home_goals,
                            away_goals=away_goals,
                            status='finished',
                            source='fotmob'
                        )
                        count += 1
                
                print(f"   ✅ {league_name}: {count} matches")
                total += count
                
            except Exception as e:
                print(f"   ❌ {league_name}: {e}")
        
        return total

    def summary(self) -> dict:
        """Get database summary stats."""
        total = self.conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        finished = self.conn.execute(
            "SELECT COUNT(*) FROM matches WHERE status='finished'"
        ).fetchone()[0]
        predictions = self.conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        leagues = self.conn.execute(
            "SELECT DISTINCT league FROM matches"
        ).fetchall()
        
        return {
            'total_matches': total,
            'finished': finished,
            'predictions': predictions,
            'leagues': [r['league'] for r in leagues],
        }

    def close(self):
        self.conn.close()
