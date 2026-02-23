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
| **Markets** | 1X2 + O/U 2.5 + BTTS | 7 markets per match for more edge opportunities |

## Daily Workflow
```bash
python daily_runner.py       # Does EVERYTHING: resolve → reseed → fit → predict → bet
```
**Smart defaults**: Auto-reseeds & refits if params are >24h old. Idempotent (won't re-run same day unless `--force`).

**Manual overrides** (optional):
- `--resolve` — Only resolve pending bets
- `--fit` — Force parameter refit
- `--calibrate` — Show accuracy report
- `--dry-run` — Preview without placing bets
- `--force` — Re-run even if already ran today

## Key Features
- **Auto Bet Resolution**: Pending bets resolved automatically from FotMob scores (manual fallback if not found)
- **1X2 Dedup**: Max 1 bet per 1X2 market per match (highest EV selected)
- **Prediction Logging**: Every prediction + odds stored in SQLite for calibration
- **Experiment Logging**: Bet summaries auto-appended to `EXPERIMENT.md`

## Roadmap
- **CLV Tracking**: Compare bet odds vs closing line to measure true edge
- **Player Stats**: Moving from team-level to player-weighted ratings
- **Calibration Correction**: Apply log-loss penalty as a shrinkage factor

---

## Technical Debt / Known Issues
- `None` display in match times (fixed: now omits if missing)
- FotMob match detail API (403): Cannot get per-match xG; results-based MLE used instead.
- The Odds API Credits: 500/month limit. Totals market consumes extra credits.
