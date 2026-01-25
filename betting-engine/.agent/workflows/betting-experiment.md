---
description: How to run the daily betting experiment
---

# Daily Betting Experiment Workflow

## Prerequisites
- Python virtual environment at `./venv`
- Chrome browser installed (for Selenium)

## Steps

// turbo-all

### 1. Read Context
First, read the context file to understand the current state:
```
View file: c:/Users/Seve/BetAI/betting-engine/CONTEXT.md
```

### 2. Check Current State
```bash
cd c:/Users/Seve/BetAI/betting-engine
cat experiment_state.json
```

### 3. Ask About Pending Bets
If there are pending bets from previous days, ask the user:
- "What were the results of yesterday's bets? (W=win, L=loss)"
- Update the state accordingly

### 4. Run Daily Script
```bash
cd c:/Users/Seve/BetAI/betting-engine
./venv/Scripts/python.exe run_experiment.py
```

### 5. Update Documentation
After running, update:
- `EXPERIMENT.md` with today's bets
- `CONTEXT.md` with any learnings

### 6. Open Dashboard
```bash
cd c:/Users/Seve/BetAI/betting-engine
start dashboard.html
```

## Key Files
- `run_experiment.py` - Main daily script
- `experiment_state.json` - Persistent state (bankroll, bets)
- `dashboard.html` - Visual progress tracker
- `CONTEXT.md` - Memory for AI continuity
