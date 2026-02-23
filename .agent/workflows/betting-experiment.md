---
description: How to run the daily betting experiment
---

# Daily Betting Experiment Workflow

// turbo-all

## Prerequisites
- Python virtual environment activated
- `.env` file with `ODDS_API_KEY` set (free at https://the-odds-api.com)

## Daily Steps

1. Read the current experiment context:
```bash
cat c:/Users/Seve/BetAI/CONTEXT.md
```

2. Check current experiment state:
```bash
cat c:/Users/Seve/BetAI/experiment_state.json
```

3. Run the daily experiment pipeline (single command does everything):
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py
```

This single command will automatically:
- Auto-fit model if parameters are >24h old (reseeds DB first)
- Resolve pending bets from FotMob results
- Fetch today's matches and odds (with 1hr cache)
- Generate predictions across 7 markets (1X2, O/U 2.5, BTTS)
- Find and display value bets
- It is **idempotent** — safe to re-run (skips if already ran today)

4. For dry-run preview (no bets placed):
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --dry-run
```

5. To only resolve pending bets:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --resolve
```

6. To force re-run (even if already ran today):
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --force
```

7. To force refit model parameters:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --fit
```

8. To check model calibration:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --calibrate
```

9. To reset the experiment fresh:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --reset
```

## Key Files
- `daily_runner.py` - Main entry point (the ONLY script you need to run)
- `experiment_state.json` - Persistent experiment state (includes bankroll_history for chart)
- `CONTEXT.md` - AI continuity context
- `EXPERIMENT.md` - Experiment documentation/log (auto-updated)
- `index.html` - Live dashboard (reads experiment_state.json)
- `src/engine/prediction_engine.py` - Dixon-Coles prediction model
- `src/engine/model_fitter.py` - MLE parameter fitting
- `src/engine/match_history.py` - SQLite match database
- `src/ingestion/odds_api.py` - The Odds API client (cached, free tier)
- `src/ingestion/fotmob_scraper.py` - FotMob results/stats data
