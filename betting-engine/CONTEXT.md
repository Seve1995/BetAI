# 🧠 Betting AI - Context for Future Sessions

> **IMPORTANT**: Read this file at the start of ANY new conversation about this project.
> This ensures continuity of the 1-month betting experiment.

---

## 🎯 What This Project Is

A **1-month value betting experiment** (Jan 25 - Feb 25, 2026) where:
- We start with **€100 virtual bankroll**
- AI finds bets with **positive Expected Value (+EV)**
- Uses **xG data** from Understat + **real odds** from Oddsportal
- Tracks wins/losses and **learns from mistakes**

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `run_experiment.py` | **DAILY SCRIPT** - run this every day |
| `experiment_state.json` | **PERSISTENT STATE** - bankroll, bets, stats |
| `EXPERIMENT.md` | Human-readable experiment log |
| `dashboard.html` | Visual dashboard (open in browser) |
| `value_bets.py` | Standalone value bet finder |
| `src/ingestion/odds_scraper.py` | Oddsportal scraper |

---

## 📊 Current State (Last Updated: 2026-01-25)

```
Day: 1/31
Bankroll: €75.16 (started €100)
Pending Bets: 6
Completed: 0
ROI: 0%
```

### Today's Bets (Day 1)
1. Atletico vs Mallorca → 2 @ 9.73 (€2.10)
2. Paris FC vs Angers → 2 @ 4.61 (€2.95)
3. Alaves vs Betis → 2 @ 2.83 (€5.09)
4. **Brentford vs Forest → 1 @ 1.85 (€8.92)** ← biggest stake
5. Real Sociedad vs Celta → 2 @ 3.55 (€2.62)
6. Roma vs Milan → 2 @ 2.85 (€3.16)

---

## 🔧 How to Continue the Experiment

### Daily Workflow
```bash
cd c:/Users/Seve/BetAI/betting-engine
python run_experiment.py
```

1. Script asks for results of pending bets (W/L/P)
2. Scrapes today's odds and xG
3. Finds new value bets
4. Asks for confirmation
5. Updates state and dashboard

### Check Dashboard
Open `dashboard.html` in browser - shows bankroll chart, bets, ROI.

---

## 📐 Strategy Parameters

| Parameter | Value | Meaning |
|-----------|-------|---------|
| MIN_EV | 5% | Only bet if EV > 5% |
| MIN_EDGE | 3% | Only bet if our prob > implied + 3% |
| KELLY_FRACTION | 25% | Use 1/4 Kelly for safety |
| MAX_SINGLE | 10% | Max 10% bankroll per bet |
| MAX_DAILY | 25% | Max 25% bankroll per day |

---

## 🧮 The Math

### Expected Value (EV)
```
EV = (our_prob × (odds - 1)) - (1 - our_prob)
```
If EV > 0, it's a **value bet**.

### Kelly Criterion (stake sizing)
```
kelly = (odds - 1) × prob - (1 - prob) / (odds - 1)
stake = kelly × 0.25 × bankroll  # quarter Kelly
```

### Probability Model
- Uses **Poisson distribution** on expected goals
- xG weighted: 50% season avg, 30% recent form, 20% actual goals
- Home advantage: 1.12x multiplier

---

## 📝 Learnings Log

### Week 1
- **Day 1**: Found 6 value bets, avg EV +39%. Heavy on away wins (5/6). Biggest stake on Brentford (highest edge at 16.4%).

*(Update this section daily with observations)*

---

## ⚠️ Important Notes for Future Sessions

1. **ALWAYS check `experiment_state.json`** for current bankroll and pending bets
2. **Ask user for bet results** before analyzing new day
3. **Update EXPERIMENT.md** after each run
4. **Refresh dashboard** to show latest data
5. **Track learnings** to improve strategy over time

---

## 🔄 Strategy Evolution

| Version | Change | Date | Reason |
|---------|--------|------|--------|
| 1.0 | Initial | 2026-01-25 | Baseline strategy |

*(Add rows when strategy is modified based on learnings)*

---

## 📞 Contact with User

The user (Seve) runs this experiment daily. When starting a new session:
1. Read this file first
2. Check current state in `experiment_state.json`
3. Ask if there are bet results to record
4. Then proceed with daily analysis
