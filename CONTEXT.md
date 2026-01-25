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

## 📊 Current State (Last Updated: 2026-01-25)

```
Day: 1/31
Bankroll: €75.64 (started €100)
Pending Bets: 8
Completed: 0
ROI: 0%
Model Version: 1.1 (Fixed)
```

### Today's Bets (Day 1 - Fixed)
1. Paris FC vs Angers → 2 @ 4.61 (€2.41)
2. Alaves vs Betis → 2 @ 2.82 (€4.20)
3. Arsenal vs Man Utd → 2 @ 5.48 (€1.52)
4. **Brentford vs Forest → 1 @ 1.84 (€7.86)**
5. Crystal Palace vs Chelsea → 1 @ 3.46 (€2.62)
6. Real Sociedad vs Celta → 2 @ 3.54 (€2.20)
7. Genoa vs Bologna → 1 @ 3.28 (€1.99)
8. Lille vs Strasbourg → 1 @ 2.40 (€1.56)

---

## 📐 Strategy Parameters (v1.1)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| MIN_EV | 5% | Only bet if EV > 5% |
| MIN_EDGE | 3% | Only bet if our prob > implied + 3% |
| KELLY_FRACTION | 25% | Use 1/4 Kelly for safety |
| MAX_SINGLE | 10% | Max 10% bankroll per bet |
| MAX_DAILY | 25% | Max 25% bankroll per day |
| **MAX_ODDS** | **6.0** | Avoid extreme longshots |

---

## 🧮 The Math (v1.1 Fixed)

### Corrected Probability Model
- **home_xg** = home_attack × away_defense_weakness × league_avg × home_advantage
- **away_xg** = away_attack × home_defense_weakness × league_avg
- *Attack Strength* = team_xg / league_avg
- *Defense Weakness* = team_xga / league_avg
- Regression: 70% model prediction, 30% recent form

---

## 📝 Learnings Log

### Week 1
- **Day 1**: Found bug in xG calculation where defensive factors were incorrectly applied (multiplying by low values for strong defenses). Fixed in v1.1. Added `max_odds` limit of 6.0 to reduce variance.

---

## 🔄 Strategy Evolution

| Version | Change | Date | Reason |
|---------|--------|------|--------|
| 1.0 | Initial | 2026-01-25 | Baseline (Buggy xG) |
| 1.1 | Fixed xG | 2026-01-25 | Correct defensive factors + Max Odds 6.0 |
