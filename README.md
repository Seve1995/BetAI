# 🎰 BetAI - Value Betting Engine

An AI-powered betting system that finds **+EV (positive Expected Value)** bets by combining:
- **xG predictions** from Understat
- **Real-time odds** from Oddsportal
- **Poisson probability model**
- **Kelly Criterion** for optimal stake sizing

## 🌐 Live Dashboard

**[seve1995.github.io/BetAI](https://seve1995.github.io/BetAI/)**

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python value_bets.py
```

## 📁 Structure

```
├── index.html             # Dashboard (GitHub Pages)
├── value_bets.py          # Main value betting engine
├── run_experiment.py      # Daily experiment runner
├── experiment_state.json  # Persistent state
├── EXPERIMENT.md          # Experiment log
├── src/ingestion/         # Scrapers (Oddsportal, Understat)
└── src/models/            # Prediction models
```

## 📊 The Math

```
EV = (our_prob × (odds - 1)) - (1 - our_prob)
```
Only bets where **EV > 5%** and **Edge > 3%** are recommended.

## 🎰 1-Month Experiment

Running Jan 25 - Feb 25, 2026:
- Starting: €100
- Day 1: 6 bets placed, €24.84 staked

See [EXPERIMENT.md](./EXPERIMENT.md) for updates.

## ⚠️ Disclaimer

Educational purposes only. Bet responsibly.
