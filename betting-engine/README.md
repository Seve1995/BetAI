# 💰 Value Betting Engine

An AI-powered betting system that finds **+EV (positive Expected Value)** bets by combining:
- **xG predictions** from Understat
- **Real-time odds** from Oddsportal
- **Poisson probability model**
- **Kelly Criterion** for optimal stake sizing

## 🎯 How It Works

```
Understat xG Data + Oddsportal Odds → Poisson Model → Find bets where Our Prob > Implied Prob
```

The system only recommends bets where:
- Expected Value > 5%
- Edge (our prob - implied prob) > 3%

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the value betting engine
python value_bets.py

# Or run the daily experiment
python run_experiment.py
```

## 📁 Project Structure

```
betting-engine/
├── value_bets.py          # Main value betting engine
├── run_experiment.py      # Daily experiment runner
├── predict_today.py       # Quick predictions (no odds)
├── dashboard.html         # Visual dashboard
├── experiment_state.json  # Persistent state
├── EXPERIMENT.md          # Experiment log
├── CONTEXT.md             # AI memory/context
├── src/
│   ├── ingestion/
│   │   ├── odds_scraper.py    # Oddsportal scraper
│   │   └── today_scraper.py   # Understat scraper
│   ├── models/
│   │   └── predictor.py       # Prediction models
│   └── core/
│       └── db_manager.py      # Database management
└── data/                  # Local data storage
```

## 📊 The Math

### Expected Value
```
EV = (our_prob × (odds - 1)) - (1 - our_prob)
```

### Kelly Criterion (stake sizing)
```
kelly = ((odds - 1) × prob - (1 - prob)) / (odds - 1)
stake = kelly × 0.25 × bankroll  # Quarter Kelly for safety
```

### Poisson Model
- Uses expected goals (xG) to predict score probabilities
- Weighted: 50% season avg, 30% recent form, 20% actual goals
- Home advantage multiplier: 1.12x

## 🎰 1-Month Experiment

Running a live experiment from **Jan 25 - Feb 25, 2026**:
- Starting bankroll: €100
- Daily value bet identification
- Track wins/losses and ROI
- Learn and adapt strategy

See `EXPERIMENT.md` for daily updates.

## 📈 Dashboard

Open `dashboard.html` in a browser to see:
- Bankroll chart over time
- Win rate and ROI
- Recent bet history
- Strategy parameters

Supports light/dark mode toggle.

## ⚙️ Configuration

Strategy parameters in `experiment_state.json`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| min_ev | 5% | Minimum Expected Value |
| min_edge | 3% | Minimum probability edge |
| kelly_fraction | 25% | Fraction of Kelly stake |
| max_single_stake | 10% | Max % of bankroll per bet |
| max_daily_stake | 25% | Max % of bankroll per day |

## 🔧 Requirements

- Python 3.8+
- Chrome browser (for Selenium)
- See `requirements.txt` for packages

## ⚠️ Disclaimer

This is for **educational purposes only**. Gambling involves risk. Past performance does not guarantee future results. Please bet responsibly.

## 📜 License

MIT
