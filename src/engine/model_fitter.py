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
"""

import json
import os
import math
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
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


def _dc_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles correction factor for low-scoring outcomes."""
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    elif x == 1 and y == 0:
        return 1 + mu * rho
    elif x == 0 and y == 1:
        return 1 + lam * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


def _dc_log_likelihood(params: np.ndarray, matches: list, team_index: dict,
                        n_teams: int) -> float:
    """
    Negative log-likelihood for Dixon-Coles model.
    
    Parameters layout:
        params[0:n_teams]       = attack strengths (log scale)
        params[n_teams:2n]      = defense strengths (log scale) 
        params[2n]              = home advantage (log scale)
        params[2n+1]            = rho (Dixon-Coles correlation)
    """
    attacks = np.exp(params[:n_teams])
    defenses = np.exp(params[n_teams:2*n_teams])
    home_adv = np.exp(params[2*n_teams])
    rho = params[2*n_teams + 1]
    
    # Clamp rho to valid range
    rho = max(-0.5, min(0.5, rho))
    
    neg_log_lik = 0.0
    
    for match in matches:
        home_idx = team_index.get(match['home'])
        away_idx = team_index.get(match['away'])
        
        if home_idx is None or away_idx is None:
            continue
        
        home_goals = match['home_goals']
        away_goals = match['away_goals']
        weight = match.get('weight', 1.0)
        
        # Expected goals
        lam = attacks[home_idx] * defenses[away_idx] * home_adv
        mu = attacks[away_idx] * defenses[home_idx]
        
        # Clamp to prevent numerical issues
        lam = max(0.1, min(10.0, lam))
        mu = max(0.1, min(10.0, mu))
        
        # Poisson log-likelihood
        log_p_home = poisson.logpmf(home_goals, lam)
        log_p_away = poisson.logpmf(away_goals, mu)
        
        # Dixon-Coles correction
        tau = _dc_tau(home_goals, away_goals, lam, mu, rho)
        tau = max(1e-10, tau)  # Prevent log(0)
        
        neg_log_lik -= weight * (log_p_home + log_p_away + math.log(tau))
    
    # Regularization: penalize extreme ratings
    # Soft constraint: mean of attacks should be ~1.0
    mean_attack = np.mean(attacks)
    neg_log_lik += 10.0 * (mean_attack - 1.0) ** 2
    
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
        
        # Add time-decay weights
        for m in matches:
            m['weight'] = _time_weight(m['date'], reference_date)
        
        # Build team index
        teams = sorted(set(
            [m['home'] for m in matches] + [m['away'] for m in matches]
        ))
        team_index = {t: i for i, t in enumerate(teams)}
        n_teams = len(teams)
        
        # Initial parameters
        # Start with neutral ratings (attack=1, defense=1, HA=1.15)
        x0 = np.zeros(2 * n_teams + 2)
        x0[:n_teams] = 0.0          # log(1.0) = 0
        x0[n_teams:2*n_teams] = 0.0  # log(1.0) = 0
        x0[2*n_teams] = math.log(1.15)  # Home advantage
        x0[2*n_teams + 1] = -0.05       # rho
        
        # Optimize
        result = minimize(
            _dc_log_likelihood,
            x0,
            args=(matches, team_index, n_teams),
            method='L-BFGS-B',
            options={'maxiter': 500, 'ftol': 1e-8},
        )
        
        if not result.success:
            print(f"   ⚠️  {league}: optimizer warning: {result.message}")
        
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
        
        for league in sorted(leagues):
            result = self.fit_league(league)
            if result:
                top_att = sorted(result['attacks'].items(), key=lambda x: x[1], reverse=True)[:3]
                top_def = sorted(result['defenses'].items(), key=lambda x: x[1])[:3]
                
                print(f"   ✅ {league}: {result['n_matches']} matches, "
                      f"HA={result['home_advantage']:.3f}, ρ={result['rho']:.4f}")
                print(f"      Top attack: {', '.join(f'{t}({v:.2f})' for t,v in top_att)}")
                print(f"      Best defense: {', '.join(f'{t}({v:.2f})' for t,v in top_def)}")
        
        return self.fitted_params
    
    def save(self, path: str = None):
        """Save fitted parameters to JSON."""
        path = path or PARAMS_FILE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.fitted_params, f, indent=2)
        print(f"\n   💾 Parameters saved to {path}")
    
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
