# 📜 BetAI Model Changelog

## [v2.2] — 2026-02-23 (Current)
### Added
- **Learning Engine**: SQLite database tracking all historical matches (~1,200).
- **MLE Fitting**: Dixon-Coles parameters are now fitted via Maximum Likelihood Estimation instead of using xG averages.
- **Calibration Engine**: Brier Score and Log-Loss calculation on historical predictions.

### Improved
- **Auto Bet Resolution**: Pending bets are automatically resolved using FotMob match results (no manual input).
- **1X2 Deduplication**: Max 1 bet per 1X2 market per match (picks highest EV).
- **BTTS Market**: Added Both Teams To Score (Yes/No) to value bet evaluation (7 markets total).
- **Prediction Logging**: Every prediction + odds stored in SQLite for calibration tracking.
- **Auto-Reseed**: `--fit` now automatically fetches latest match results before fitting.
- **Experiment Logging**: Auto-appends bet summaries to `EXPERIMENT.md` after placing bets.
- **Bankroll Rounding**: All bankroll mutations rounded to 2dp to prevent float drift.

## [v2.1] — 2026-02-23
### Added
- **Venue Splits**: Separate attack/defense ratings for Home and Away matches.
- **Bayesian Shrinkage**: Regressing ratings toward the mean for teams with few matches.
- **Empirical HA**: Per-league home advantage factors.
- **Totals Market**: Integration of Over/Under 2.5 goals odds.

## [v2.0] — 2026-02-23
### Added
- **Unified Pipeline**: Replaced 7+ separate scripts with `daily_runner.py`.
- **Dixon-Coles Core**: Implementation of the canonical Poisson model with $\rho$ correction.
- **The Odds API**: Automated live odds fetching.
- **FotMob Integration**: Clean API-based xG fetching.

## [v1.0] — Jan 2026
### Added
- **Initial Concept**: Script-based Understat scraping and basic Poisson modeling.
- **Manual Mapping**: Heavy reliance on hardcoded team name aliases.
- **Limited Scope**: 1X2 market only.
