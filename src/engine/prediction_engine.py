"""
PREDICTION ENGINE - Dixon-Coles Poisson Model v2.1
===================================================

The SINGLE source of truth for match outcome predictions.
Uses a Dixon-Coles inspired Poisson model with:
  - Venue-specific (home/away) attack/defense strength ratings
  - Bayesian-shrunk ratings (more conservative with small samples)
  - Per-league empirical home advantage (not hardcoded)
  - Low-score correlation adjustment (Dixon-Coles tau)

Markets: 1X2, Over/Under 2.5, BTTS
"""

import numpy as np
from scipy.stats import poisson

MAX_GOALS = 8            # Max goals per team in Poisson grid

# Dixon-Coles tau correction for low-scoring outcomes
DC_RHO = -0.05           # Slight negative correlation (0-0 / 1-1 correction)

# Default home advantage (used only if per-league HA unavailable)
DEFAULT_HOME_ADVANTAGE = 1.12


def _dixon_coles_tau(x: int, y: int, lambda_h: float, lambda_a: float, rho: float) -> float:
    """
    Dixon-Coles correction factor for low-scoring games.
    Adjusts P(0-0), P(1-0), P(0-1), P(1-1) to account for 
    the well-known correlation in football scoring.
    """
    if x == 0 and y == 0:
        return 1 - lambda_h * lambda_a * rho
    elif x == 1 and y == 0:
        return 1 + lambda_a * rho
    elif x == 0 and y == 1:
        return 1 + lambda_h * rho
    elif x == 1 and y == 1:
        return 1 - rho
    else:
        return 1.0


class PredictionEngine:
    """
    Predicts match outcomes using a Dixon-Coles corrected Poisson model.
    
    v2.2: Uses MLE-fitted parameters when available, falls back to xG-based.
    
    Modes:
    1. FITTED (preferred): Uses MLE-fitted attack/defense/rho/HA from model_fitter
    2. XG-BASED (fallback): Uses xG-derived venue-specific ratings from stats_manager
    """
    
    def __init__(self, stats_manager, fitted_params: dict = None):
        self.stats_manager = stats_manager
        self.fitted_params = fitted_params or {}
        self._mode_log = {}  # Track which mode was used per match

    def predict_match(self, league_name: str, home_team: str, away_team: str) -> dict | None:
        """
        Predict match outcomes and probabilities.
        
        Tries MLE-fitted parameters first, falls back to xG-based ratings.
        
        Returns:
            Dict with probabilities for all markets, or None if data unavailable
        """
        # --- Try MLE-fitted parameters first ---
        league_fit = self.fitted_params.get(league_name)
        if league_fit:
            result = self._predict_fitted(league_name, home_team, away_team, league_fit)
            if result:
                return result
        
        # --- Fallback to xG-based ratings ---
        return self._predict_xg_based(league_name, home_team, away_team)

    def _predict_fitted(self, league_name: str, home_team: str, away_team: str,
                        league_fit: dict) -> dict | None:
        """Predict using MLE-fitted parameters."""
        attacks = league_fit.get('attacks', {})
        defenses = league_fit.get('defenses', {})
        
        home_att = self._fuzzy_lookup(attacks, home_team)
        home_def = self._fuzzy_lookup(defenses, home_team)
        away_att = self._fuzzy_lookup(attacks, away_team)
        away_def = self._fuzzy_lookup(defenses, away_team)
        
        if home_att is None or away_att is None:
            return None  # Team not in fitted data
        
        ha = league_fit.get('home_advantage', DEFAULT_HOME_ADVANTAGE)
        rho = league_fit.get('rho', DC_RHO)
        
        # Dixon-Coles expected goals
        home_lambda = home_att * away_def * ha
        away_lambda = away_att * home_def
        
        # Clamp
        home_lambda = max(0.3, min(4.0, home_lambda))
        away_lambda = max(0.3, min(4.0, away_lambda))
        
        self._mode_log[f"{home_team} vs {away_team}"] = "MLE-fitted"
        return self._build_prediction(home_lambda, away_lambda, rho, "fitted")

    def _predict_xg_based(self, league_name: str, home_team: str, 
                          away_team: str) -> dict | None:
        """Predict using xG-derived ratings (fallback)."""
        home_stats = self.stats_manager.get_team_stats(league_name, home_team)
        away_stats = self.stats_manager.get_team_stats(league_name, away_team)
        
        if not home_stats or not away_stats:
            return None
        
        league_avg = home_stats['league_avg_xg']
        home_advantage = home_stats.get('home_advantage', DEFAULT_HOME_ADVANTAGE)
        
        home_lambda = (
            home_stats['home_att'] * away_stats['away_def'] * league_avg * home_advantage
        )
        away_lambda = (
            away_stats['away_att'] * home_stats['home_def'] * league_avg
        )
        
        home_lambda = max(0.3, min(4.0, home_lambda))
        away_lambda = max(0.3, min(4.0, away_lambda))
        
        self._mode_log[f"{home_team} vs {away_team}"] = "xG-based"
        return self._build_prediction(home_lambda, away_lambda, DC_RHO, "xg")

    def _fuzzy_lookup(self, mapping: dict, team: str):
        """Look up team in a dict, trying exact then fuzzy match."""
        if team in mapping:
            return mapping[team]
        team_lower = team.lower()
        for key in mapping:
            if team_lower in key.lower() or key.lower() in team_lower:
                return mapping[key]
        return None

    def _build_prediction(self, home_lambda: float, away_lambda: float, 
                          rho: float, source: str) -> dict:
        
        # --- Build Poisson probability matrix ---
        h_probs = poisson.pmf(range(MAX_GOALS), home_lambda)
        a_probs = poisson.pmf(range(MAX_GOALS), away_lambda)
        
        # Raw matrix
        matrix = np.outer(h_probs, a_probs)
        
        # Apply Dixon-Coles correction for low-scoring games
        for i in range(min(2, MAX_GOALS)):
            for j in range(min(2, MAX_GOALS)):
                tau = _dixon_coles_tau(i, j, home_lambda, away_lambda, rho)
                matrix[i, j] *= tau
        
        # Renormalize after DC adjustment
        matrix /= matrix.sum()
        
        # --- Extract market probabilities ---
        home_win = float(np.sum(np.tril(matrix, -1)))
        draw = float(np.sum(np.diag(matrix)))
        away_win = float(np.sum(np.triu(matrix, 1)))
        
        # Over/Under 2.5
        under_25 = sum(
            matrix[i, j] for i in range(MAX_GOALS) for j in range(MAX_GOALS) if i + j <= 2
        )
        over_25 = 1 - under_25
        
        # BTTS (Both Teams To Score)
        no_btts = float(sum(matrix[0, :]) + sum(matrix[:, 0]) - matrix[0, 0])
        btts = 1 - no_btts
        
        # Most likely correct score
        flat_idx = np.argmax(matrix)
        most_likely_h = flat_idx // MAX_GOALS
        most_likely_a = flat_idx % MAX_GOALS
        
        return {
            'home_xg': home_lambda,
            'away_xg': away_lambda,
            'source': source,
            'rho_used': rho,
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'over_25': float(over_25),
            'under_25': float(under_25),
            'btts': float(btts),
            'most_likely_score': f"{most_likely_h}-{most_likely_a}",
            'most_likely_score_prob': float(matrix[most_likely_h, most_likely_a]),
        }
    
    def calculate_ev(self, our_prob: float, odds: float) -> float:
        """Calculate Expected Value: EV = (prob × (odds - 1)) - (1 - prob)"""
        return (our_prob * (odds - 1)) - (1 - our_prob)
    
    def calculate_edge(self, our_prob: float, odds: float) -> float:
        """Calculate edge over bookmaker: our probability - implied probability"""
        return our_prob - (1 / odds)
    
    def calculate_kelly(self, our_prob: float, odds: float, 
                         fraction: float = 0.25, max_pct: float = 0.10) -> float:
        """
        Calculate optimal stake using fractional Kelly Criterion.
        
        Args:
            our_prob: Our estimated probability of winning
            odds: Decimal odds offered
            fraction: Kelly fraction (0.25 = quarter Kelly for safety)
            max_pct: Maximum percentage of bankroll
            
        Returns:
            Optimal stake as fraction of bankroll (0 to max_pct)
        """
        b = odds - 1
        if b <= 0:
            return 0
        
        q = 1 - our_prob
        kelly = (b * our_prob - q) / b
        
        if kelly <= 0:
            return 0
        
        kelly *= fraction
        return min(kelly, max_pct)
    
    def find_value_bets(self, league: str, home: str, away: str, 
                         odds: dict, strategy: dict) -> list:
        """
        Find value bets for a match given real odds.
        
        Supports 5 markets: 1, X, 2, Over 2.5, Under 2.5
        
        Args:
            league: League name
            home: Home team name
            away: Away team name
            odds: Dict with '1', 'X', '2', 'over_25', 'under_25' keys
            strategy: Dict with min_ev, min_edge, kelly_fraction, etc.
            
        Returns:
            List of value bet dicts
        """
        pred = self.predict_match(league, home, away)
        if not pred:
            return []
        
        max_odds = strategy.get('max_odds', 6.0)
        min_ev = strategy.get('min_ev', 0.05)
        min_edge = strategy.get('min_edge', 0.03)
        kelly_frac = strategy.get('kelly_fraction', 0.25)
        max_single = strategy.get('max_single_stake_pct', 0.10)
        
        # All markets we can bet on
        markets = [
            ('1', pred['home_win'], odds.get('1'), f"1 ({home})"),
            ('X', pred['draw'], odds.get('X'), "X (Draw)"),
            ('2', pred['away_win'], odds.get('2'), f"2 ({away})"),
            ('Over 2.5', pred['over_25'], odds.get('over_25'), "Over 2.5 Goals"),
            ('Under 2.5', pred['under_25'], odds.get('under_25'), "Under 2.5 Goals"),
            ('BTTS Yes', pred['btts'], odds.get('btts_yes'), "Both Teams To Score"),
            ('BTTS No', 1 - pred['btts'], odds.get('btts_no'), "No BTTS"),
        ]
        
        value_bets = []
        
        for market, prob, real_odds, tip in markets:
            if not real_odds or real_odds <= 1 or real_odds > max_odds:
                continue
            
            ev = self.calculate_ev(prob, real_odds)
            edge = self.calculate_edge(prob, real_odds)
            
            if ev >= min_ev and edge >= min_edge:
                kelly_pct = self.calculate_kelly(prob, real_odds, kelly_frac, max_single)
                
                value_bets.append({
                    'market': market,
                    'tip': tip,
                    'prob': prob,
                    'odds': real_odds,
                    'implied_prob': 1 / real_odds,
                    'ev': ev,
                    'edge': edge,
                    'kelly_pct': kelly_pct,
                    'home_xg': pred['home_xg'],
                    'away_xg': pred['away_xg'],
                    'prediction': pred,
                })
        
        value_bets.sort(key=lambda x: x['ev'], reverse=True)
        return value_bets
