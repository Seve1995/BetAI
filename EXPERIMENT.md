# 💰 Betting Experiment v2.2

## Experiment Rules

| Parameter | Value |
|-----------|-------|
| **Start Date** | Feb 23, 2026 |
| **End Date** | Mar 25, 2026 |
| **Initial Bankroll** | €100.00 |
| **Model** | Dixon-Coles Poisson v2.2 (MLE-Fitted) |
| **Markets** | 1X2, Over/Under 2.5 |
| **Objective** | Maximize bankroll via calibrated value betting |

---

## Current Status

| Metric | Value |
|--------|-------|
| **Bankroll** | €100.00 |
| **Day** | 1/31 |
| **Total Bets** | 0 |
| **ROI** | 0.0% |

---

## v2.2 Model Architecture (Learning Engine)

- **Matches Seeded**: 1,189 (completed matches this season)
- **Parameter Fitting**: Dixon-Coles MLE (optimizing attack, defense, HA, and $\rho$ jointly)
- **Time Decay**: 180-day half-life for historical weighting
- **Accuracy Tracking**: Brier Score and Log-Loss calculation on predictions

---

## Daily Log

_New experiment cycle starting. Run `python daily_runner.py` for fresh Day 1 bets._
