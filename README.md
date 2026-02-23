# 🎰 BetAI — AI-Powered Value Betting Engine

An automated value betting system that uses **MLE-fitted Dixon-Coles Poisson predictions** to find +EV bets across Europe's top 5 football leagues.

## How It Works

```
FotMob API                The Odds API
     │                         │
     ▼                         ▼
Match History DB  ──▶  Live Odds Discovery
     │                         │
     ▼                         │
MLE Parameter Fitter  ◀────────┘
     │
     ▼
Prediction Engine (v2.2)
     │
     ▼
Value Bet Identification (+EV > 5%)
```

## Quick Start

echo "ODDS_API_KEY=your_key_here" > .env

# 4. Run
python daily_runner.py --dry-run   # Preview
python daily_runner.py             # Full run
```

## Model

**Dixon-Coles corrected Poisson** using expected goals (xG) data:

- Team attack/defense strength from season xG, normalized to league averages
- Home advantage factor (1.12×)
- Low-score correlation adjustment (ρ = -0.05)
- Predictions for **1X2**, **Over/Under 2.5**, and **BTTS** markets
- **Fractional Kelly Criterion** (25%) for stake sizing

## Strategy Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min EV | 5% | Only bet when expected value is meaningful |
| Min Edge | 3% | Filter out noise from model error |
| Kelly Fraction | 25% | Conservative staking to survive variance |
| Max Single Bet | 10% bankroll | Prevent catastrophic single losses |
| Max Daily Exposure | 25% bankroll | Limit daily risk |
| Max Odds | 6.0 | Avoid longshots where model is unreliable |

## Leagues

Serie A · Premier League · La Liga · Bundesliga · Ligue 1

## CLI Reference

```bash
python daily_runner.py                 # Full pipeline
python daily_runner.py --dry-run       # Preview only (no state changes)
python daily_runner.py --predictions-only  # Predictions without odds
python daily_runner.py --resolve       # Only resolve pending bets
python daily_runner.py --reset         # Reset experiment to fresh start
```

## Dashboard

Open `index.html` in a browser to see a live dashboard. It reads from `experiment_state.json` and auto-refreshes every 30 seconds.

## Project Structure

```
BetAI/
├── daily_runner.py              # Entry point — the only script you run
├── experiment_state.json        # Persistent experiment state
├── index.html                   # Live dashboard (dark/light theme)
├── requirements.txt
├── .env                         # ODDS_API_KEY (not tracked by git)
├── CONTEXT.md                   # AI continuity context
├── EXPERIMENT.md                # Experiment log
├── src/
│   ├── engine/
│   │   ├── prediction_engine.py # Dixon-Coles Poisson model
│   │   └── stats_manager.py     # Team xG stats + fuzzy matching
│   ├── ingestion/
│   │   ├── fotmob_scraper.py    # FotMob API (xG, matches)
│   │   └── odds_api.py          # The Odds API (odds, scores)
│   └── core/
│       └── config.py            # Centralized settings
└── archive/                     # Deprecated scripts (kept for reference)
```

## Data Sources

| Source | Purpose | Cost |
|--------|---------|------|
| [FotMob](https://www.fotmob.com) | Team xG stats, match schedules | Free |
| [The Odds API](https://the-odds-api.com) | Live odds, match scores | Free tier (500 req/month) |

## License

MIT
