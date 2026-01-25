"""
Match Predictor - Unified Betting Engine
========================================

Modello di Poisson basato su xG (Expected Goals) per predire risultati.
"""

import numpy as np
from scipy.stats import poisson
from ..core.db_manager import DatabaseManager, Match, AdvancedStat

class MatchPredictor:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_team_avg_xg(self, team_name, league, last_n=10):
        """
        Calcola la media xG fatti e subiti (Attack/Defense Strength).
        """
        session = self.db.get_session()
        
        # Recupera gli ultimi N match della squadra con stats
        query = session.query(Match, AdvancedStat).join(AdvancedStat).filter(
            Match.league == league,
            (Match.home_team == team_name) | (Match.away_team == team_name)
        ).order_by(Match.date.desc()).limit(last_n).all()
        
        if not query:
            session.close()
            return None, None
            
        xg_scored = []
        xg_conceded = []
        
        for m, s in query:
            if m.home_team == team_name:
                xg_scored.append(s.home_xg)
                xg_conceded.append(s.away_xg)
            else:
                xg_scored.append(s.away_xg)
                xg_conceded.append(s.home_xg)
        
        session.close()
        return np.mean(xg_scored), np.mean(xg_conceded)

    def predict_match(self, home_team, away_team, league):
        """
        Calcola probabilità 1X2 basate su Poisson distribuendo gli xG medi.
        """
        h_att, h_def = self.get_team_avg_xg(home_team, league)
        a_att, a_def = self.get_team_avg_xg(away_team, league)
        
        if h_att is None or a_att is None:
            return None
            
        # Calcolo Expected Goals per il match specifico
        # Semplificato: media attacco squadra A vs media difesa squadra B
        home_expect = h_att * (a_def / 1.3) # 1.3 è un fattore di normalizzazione (media gol lega)
        away_expect = a_att * (h_def / 1.3)
        
        # Probabilità risultati (0-5 gol)
        max_goals = 6
        home_probs = poisson.pmf(range(max_goals), home_expect)
        away_probs = poisson.pmf(range(max_goals), away_expect)
        
        # Matrice dei risultati
        matrix = np.outer(home_probs, away_probs)
        
        home_win = np.sum(np.tril(matrix, -1))
        draw = np.sum(np.diag(matrix))
        away_win = np.sum(np.triu(matrix, 1))
        
        return {
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'home_expect': home_expect,
            'away_expect': away_expect,
            'over_2.5': 1 - (matrix[0,0] + matrix[0,1] + matrix[0,2] + 
                             matrix[1,0] + matrix[1,1] + matrix[2,0])
        }
