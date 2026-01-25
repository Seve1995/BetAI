# 🎰 BetAI - Value Betting with AI

An AI-powered betting system that finds **+EV (positive Expected Value)** bets using machine learning and statistical models.

## 📁 Projects

### [betting-engine/](./betting-engine/)
The main value betting engine:
- **xG predictions** from Understat (5 leagues)
- **Real-time odds** from Oddsportal
- **Poisson probability model** for match outcomes
- **Kelly Criterion** for optimal stake sizing
- **Visual dashboard** with live tracking

## 🚀 Quick Start

```bash
cd betting-engine
pip install -r requirements.txt
python value_bets.py
```

## 📊 Live Experiment

Running a 1-month experiment (Jan 25 - Feb 25, 2026):
- Starting bankroll: €100
- Daily value bet identification
- Track wins/losses and ROI

See [betting-engine/EXPERIMENT.md](./betting-engine/EXPERIMENT.md) for daily updates.

## 🌐 Dashboard

View the live dashboard: **[seve1995.github.io/BetAI](https://seve1995.github.io/BetAI/)**

## ⚠️ Disclaimer

For educational purposes only. Gambling involves risk. Bet responsibly.
