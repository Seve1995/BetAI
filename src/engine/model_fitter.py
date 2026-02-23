"""
MODEL FITTER - Dixon-Coles Maximum Likelihood Estimation
=========================================================

Fits team attack/defense strengths, home advantage, and the Dixon-Coles
correlation parameter (rho) from historical match results.

This is the real Dixon-Coles: instead of computing ratings from 
team-level xG averages, we jointly optimize ALL parameters to maximize
the likelihood of the observed scorelines.

Key features:
- Time-decay weighting (recent matches count more)
- Per-league fitting (each league has its own model)
- Exports fitted parameters for the prediction engine
- Vectorized likelihood for fast optimization
"""

import json
import os
import math
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln  # For fast vectorized Poisson logpmf
from datetime import datetime


# Time decay: half-life in days
HALF_LIFE_DAYS = 180
XI = math.log(2) / HALF_LIFE_DAYS  # ~0.00385

# Minimum matches required to fit a league
MIN_MATCHES = 50

# Output path for fitted parameters
PARAMS_FILE = os.path.join("data", "fitted_params.json")


def _time_weight(match_date: str, reference_date: str = None) -> float:
    """
    Exponential time-decay weight for a match.
    
    Recent matches have weight ~1.0, older matches decay toward 0.
    With half-life=180 days, a match from 6 months ago has weight 0.5.
    """
    if not reference_date:
        reference_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        d_match = datetime.strptime(match_date[:10], "%Y-%m-%d")
        d_ref = datetime.strptime(reference_date[:10], "%Y-%m-%d")
        days_ago = (d_ref - d_match).days
        return math.exp(-XI * max(days_ago, 0))
    except (ValueError, TypeError):
        return 0.5  # Default weight for unparseable dates


def _prepare_match_arrays(matches: list, team_index: dict):
    """
    Pre-compute numpy arrays from match list (called once before optimization).
    Returns a dict of arrays for vectorized likelihood computation.
    """
    n = len(matches)
    home_idx = np.zeros(n, dtype=np.int32)
    away_idx = np.zeros(n, dtype=np.int32)
    home_goals = np.zeros(n, dtype=np.int32)
    away_goals = np.zeros(n, dtype=np.int32)
    weights = np.zeros(n, dtype=np.float64)
    
    valid = 0
    for m in matches:
        hi = team_index.get(m['home'])
        ai = team_index.get(m['away'])
        if hi is None or ai is None:
            continue
        home_idx[valid] = hi
        away_idx[valid] = ai
        home_goals[valid] = m['home_goals']
        away_goals[valid] = m['away_goals']
        weights[valid] = m.get('weight', 1.0)
        valid += 1
    
    return {
        'home_idx': home_idx[:valid],
        'away_idx': away_idx[:valid],
        'home_goals': home_goals[:valid],
        'away_goals': away_goals[:valid],
        'weights': weights[:valid],
        'n': valid,
    }


def _poisson_logpmf(k, mu):
    """Vectorized Poisson log-PMF using gammaln (no Python loops)."""
    return k * np.log(mu) - mu - gammaln(k + 1)


def _dc_log_likelihood_vec(params: np.ndarray, arrays: dict,
                            n_teams: int) -> float:
    """
    Fully vectorized negative log-likelihood for Dixon-Coles model.
    
    ~100x faster than the loop-based version.
    """
    attacks = np.exp(params[:n_teams])
    defenses = np.exp(params[n_teams:2*n_teams])
    home_adv = np.exp(params[2*n_teams])
    rho = np.clip(params[2*n_teams + 1], -0.5, 0.5)
    
    hi = arrays['home_idx']
    ai = arrays['away_idx']
    hg = arrays['home_goals']
    ag = arrays['away_goals']
    w = arrays['weights']
    
    # Expected goals (vectorized fancy indexing)
    lam = np.clip(attacks[hi] * defenses[ai] * home_adv, 0.1, 10.0)
    mu = np.clip(attacks[ai] * defenses[hi], 0.1, 10.0)
    
    # Poisson log-likelihood (vectorized)
    log_p = _poisson_logpmf(hg, lam) + _poisson_logpmf(ag, mu)
    
    # Dixon-Coles tau correction (vectorized with masks)
    tau = np.ones(arrays['n'])
    m00 = (hg == 0) & (ag == 0)
    m10 = (hg == 1) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m11 = (hg == 1) & (ag == 1)
    
    tau[m00] = 1 - lam[m00] * mu[m00] * rho
    tau[m10] = 1 + mu[m10] * rho
    tau[m01] = 1 + lam[m01] * rho
    tau[m11] = 1 - rho
    
    tau = np.maximum(tau, 1e-10)
    
    # Weighted negative log-likelihood
    neg_log_lik = -np.sum(w * (log_p + np.log(tau)))
    
    # Regularization: mean attack → 1.0
    neg_log_lik += 10.0 * (np.mean(attacks) - 1.0) ** 2
    
    return neg_log_lik


class ModelFitter:
    """
    Fits Dixon-Coles model parameters via MLE.
    
    Usage:
        fitter = ModelFitter(match_history)
        params = fitter.fit_league('Premier League')
        fitter.fit_all_leagues()
        fitter.save()
    """
    
    def __init__(self, match_history):
        self.history = match_history
        self.fitted_params = {}
    
    def fit_league(self, league: str, reference_date: str = None) -> dict | None:
        """
        Fit Dixon-Coles parameters for a single league.
        
        Returns dict with:
            - attacks: {team: strength}
            - defenses: {team: strength}  
            - home_advantage: float
            - rho: float
            - n_matches: int
            - log_likelihood: float
        """
        matches = self.history.get_training_data(league=league)
        
        if len(matches) < MIN_MATCHES:
            print(f"   ⚠️  {league}: only {len(matches)} matches (need {MIN_MATCHES})")
            return None
        
        print(f"   ⏳ {league}: fitting {len(matches)} matches...", end=" ", flush=True)
        t0 = time.time()
        
        # Add time-decay weights
        for m in matches:
            m['weight'] = _time_weight(m['date'], reference_date)
        
        # Build team index
        teams = sorted(set(
            [m['home'] for m in matches] + [m['away'] for m in matches]
        ))
        team_index = {t: i for i, t in enumerate(teams)}
        n_teams = len(teams)
        
        # Pre-compute arrays for vectorized likelihood
        arrays = _prepare_match_arrays(matches, team_index)
        
        # Initial parameters
        x0 = np.zeros(2 * n_teams + 2)
        x0[2*n_teams] = math.log(1.15)  # Home advantage
        x0[2*n_teams + 1] = -0.05       # rho
        
        # Optimize (using vectorized likelihood)
        result = minimize(
            _dc_log_likelihood_vec,
            x0,
            args=(arrays, n_teams),
            method='L-BFGS-B',
            options={'maxiter': 500, 'ftol': 1e-8},
        )
        
        elapsed = time.time() - t0
        
        if not result.success:
            print(f"⚠️ ({elapsed:.1f}s, warning: {result.message})")
        else:
            print(f"✅ ({elapsed:.1f}s)")
        
        # Extract fitted parameters
        attacks = np.exp(result.x[:n_teams])
        defenses = np.exp(result.x[n_teams:2*n_teams])
        home_adv = np.exp(result.x[2*n_teams])
        rho = result.x[2*n_teams + 1]
        
        # Normalize: scale attacks so mean = 1.0
        mean_att = np.mean(attacks)
        attacks /= mean_att
        defenses *= mean_att  # Compensate
        
        fitted = {
            'attacks': {t: float(attacks[team_index[t]]) for t in teams},
            'defenses': {t: float(defenses[team_index[t]]) for t in teams},
            'home_advantage': float(home_adv),
            'rho': float(rho),
            'n_matches': len(matches),
            'n_teams': n_teams,
            'log_likelihood': float(-result.fun),
            'fitted_at': datetime.now().isoformat(),
        }
        
        self.fitted_params[league] = fitted
        return fitted
    
    def fit_all_leagues(self, leagues: list = None) -> dict:
        """Fit parameters for all leagues."""
        if not leagues:
            leagues = list(set(
                m['league'] for m in self.history.get_training_data()
            ))
        
        print("\n🧠 Fitting Dixon-Coles parameters via MLE...")
        t_total = time.time()
        
        for league in sorted(leagues):
            result = self.fit_league(league)
            if result:
                top_att = sorted(result['attacks'].items(), key=lambda x: x[1], reverse=True)[:3]
                top_def = sorted(result['defenses'].items(), key=lambda x: x[1])[:3]
                
                print(f"      HA={result['home_advantage']:.3f}, ρ={result['rho']:.4f}")
                print(f"      Top attack: {', '.join(f'{t}({v:.2f})' for t,v in top_att)}")
                print(f"      Best defense: {', '.join(f'{t}({v:.2f})' for t,v in top_def)}")
        
        print(f"\n   ⏱️  Total fitting time: {time.time() - t_total:.1f}s")
        return self.fitted_params
    
    def save(self, path: str = None):
        """Save fitted parameters to JSON."""
        path = path or PARAMS_FILE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.fitted_params, f, indent=2)
        print(f"   💾 Parameters saved to {path}")
    
    def load(self, path: str = None) -> dict:
        """Load previously fitted parameters."""
        path = path or PARAMS_FILE
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.fitted_params = json.load(f)
        return self.fitted_params
    
    def get_team_params(self, league: str, team: str) -> dict | None:
        """Get fitted attack/defense for a specific team."""
        league_params = self.fitted_params.get(league)
        if not league_params:
            return None
        
        attack = league_params['attacks'].get(team)
        defense = league_params['defenses'].get(team)
        
        if attack is None or defense is None:
            # Try fuzzy match
            team_lower = team.lower()
            for t in league_params['attacks']:
                if team_lower in t.lower() or t.lower() in team_lower:
                    attack = league_params['attacks'][t]
                    defense = league_params['defenses'][t]
                    break
        
        if attack is None:
            return None
        
        return {
            'attack': attack,
            'defense': defense,
            'home_advantage': league_params['home_advantage'],
            'rho': league_params['rho'],
        }
