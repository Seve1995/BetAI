"""
PREDICTION ENGINE - xG-based Poisson Model
==========================================
"""

import math
from scipy.stats import poisson

class PredictionEngine:
    def __init__(self, stats_manager):
        self.stats_manager = stats_manager

    def predict_match(self, league_name, home_team, away_team):
        """
        Predict match outcomes and BTTS probability.
        Expected Goals Home = Home_Att_Rating * Away_Def_Rating * League_Avg_xG
        Expected Goals Away = Away_Att_Rating * Home_Def_Rating * League_Avg_xG
        """
        home_stats = self.stats_manager.get_team_stats(league_name, home_team)
        away_stats = self.stats_manager.get_team_stats(league_name, away_team)
        
        if not home_stats or not away_stats:
            return None
            
        league_avg = home_stats['league_avg_xg']
        
        # Calculate lambda (expected goals) for both teams
        # We also need to consider Home Advantage. Historical data suggests ~1.1-1.2x.
        # Let's use a conservative 1.1x for home and 0.9x for away as a baseline.
        home_lambda = home_stats['att_rating'] * away_stats['def_rating'] * league_avg * 1.15
        away_lambda = away_stats['att_rating'] * home_stats['def_rating'] * league_avg * 0.85
        
        # Calculate probabilities from Poisson distribution
        # BTTS is 1 - (Prob home 0 + Prob away 0 - Prob both 0)
        # Prob(home > 0) = 1 - e^(-home_lambda)
        # Prob(away > 0) = 1 - e^(-away_lambda)
        # Assuming independence (standard in simple Poisson models)
        p_home_score = 1 - poisson.pmf(0, home_lambda)
        p_away_score = 1 - poisson.pmf(0, away_lambda)
        
        p_btts = p_home_score * p_away_score
        
        # Also calculate win probabilities
        p_home_win = 0
        p_away_win = 0
        p_draw = 0
        
        # Iteratively sum probabilities for scores up to 10
        for h in range(10):
            p_h = poisson.pmf(h, home_lambda)
            for a in range(10):
                p_a = poisson.pmf(a, away_lambda)
                p_score = p_h * p_a
                
                if h > a: p_home_win += p_score
                elif a > h: p_away_win += p_score
                else: p_draw += p_score
                
        return {
            'home_xg_expected': home_lambda,
            'away_xg_expected': away_lambda,
            'btts_prob': p_btts,
            'home_win_prob': p_home_win,
            'away_win_prob': p_away_win,
            'draw_prob': p_draw
        }
