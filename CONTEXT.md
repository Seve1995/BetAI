# BetAI - Experiment Context (v2.2)

## Overview
AI-powered value betting system using an MLE-fitted Dixon-Coles Poisson model.

## Current Experiment
- **Period**: Feb 23 – Mar 25, 2026
- **Bankroll**: €100.00 (Model v2.2 Reset)
- **Model**: Dixon-Coles Poisson v2.2 (Learning Engine enabled)

## Architecture
- **Entry Point**: `daily_runner.py` — unified CLI for everything
- **Inference**: `PredictionEngine (v2.2)` — uses 🧠 MLE-fitted params (fitted_params.json) with 📊 xG fallback
- **Learning**: `MatchHistory` (SQLite) + `ModelFitter` (MLE via scipy) + `Calibration` (Brier/Log-Loss)
- **Data**: FotMob (results/stats) + The Odds API (live markets)

## Model Configuration (v2.2)
| Feature | Implementation | Rationale |
|-----------|-------|-----------|
| **MLE Fitting** | Dixon-Coles MLE (goals-based) | Truly fits team strengths from outcomes |
| **Rho ($\rho$)** | Fitted per league | Better correction for low-scoring skew |
| **Home Advantage** | Empirical per league | Calibrates for league-specific HA (e.g. La Liga is high) |
| **Time Decay** | exponential ($\text{half-life}=180 \text{d}$) | Weight recent form over stale history |
| **Bayesian Shrinkage** | $k=5$ for cold-starts | Prevents noise in small samples |
| **Markets** | 1X2 + O/U 2.5 | Diversify risk and find softer lines |

## Daily Workflow
1. `python daily_runner.py --seed` (Update match DB with latest results)
2. `python daily_runner.py --fit` (Refit MLE parameters)
3. `python daily_runner.py --calibrate` (Check model accuracy)
4. `python daily_runner.py` (Generate and place bets)

## Learning Roadmap
- **Closing Choice tracking**: Track CLV (Closing Line Value) in `match_history.db`.
- **Auto-Update**: Refit automatically after matches resolve.
- **Player Stats**: Moving from team-level to player-weighted ratings.
- **Calibration Correction**: Apply log-loss penalty as a shrinkage factor.

---

## Technical Debt / Known Issues
- `None` display in match times (fixed: now omits if missing)
- FotMob match detail API (403): Cannot get per-match xG; results-based MLE used instead.
- The Odds API Credits: 500/month limit. Totals market consumes extra credits.
