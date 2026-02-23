# 📜 BetAI Model Changelog

## [v2.2] — 2026-02-23 (Current)
### Added
- **Learning Engine**: SQLite database tracking all historical matches (~1,200).
- **MLE Fitting**: Dixon-Coles parameters are now fitted via Maximum Likelihood Estimation instead of using xG averages.
- **Calibration Engine**: Brier Score and Log-Loss calculation on historical predictions.

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
