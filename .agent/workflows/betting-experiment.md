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

3. Run the daily experiment pipeline:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py
```

4. For dry-run preview (no bets placed):
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --dry-run
```

5. To only resolve pending bets:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --resolve
```

6. To reset the experiment fresh:
```bash
cd c:/Users/Seve/BetAI && .venv/Scripts/python.exe daily_runner.py --reset
```

## Key Files
- `daily_runner.py` - Main entry point (the ONLY script you need to run)
- `experiment_state.json` - Persistent experiment state
- `CONTEXT.md` - AI continuity context
- `EXPERIMENT.md` - Experiment documentation/log
- `src/engine/prediction_engine.py` - Poisson prediction model
- `src/engine/stats_manager.py` - Team xG stats management
- `src/ingestion/odds_api.py` - The Odds API client (free tier)
- `src/ingestion/fotmob_scraper.py` - FotMob xG/match data
