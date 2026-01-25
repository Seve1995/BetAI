# 💰 Betting Experiment - Gennaio/Febbraio 2026

## 📋 Regole dell'Esperimento

| Parametro | Valore |
|-----------|--------|
| **Data Inizio** | 25 Gennaio 2026 |
| **Data Fine** | 25 Febbraio 2026 |
| **Budget Iniziale** | €100.00 |
| **Obiettivo** | Massimizzare il bankroll |

---

## 📊 Stato Attuale

| Metrica | Valore |
|---------|--------|
| **Bankroll** | €75.64 |
| **Giorno** | 1/31 |
| **Scommesse Totali** | 8 |
| **Vinte** | 0 |
| **Perse** | 0 |
| **Pending** | 8 |
| **ROI** | 0.0% |

---

## 📈 Cronologia Giornaliera

### Giorno 1 - 25 Gennaio 2026
**Bankroll Iniziale**: €100.00  
**Stake Totale**: €24.36  
**Bankroll Finale**: €75.64  
**Modello**: v1.1 (Fixed xG formula + Max Odds 6.0)

#### Scommesse Piazzate (v1.1)
| # | Match | Tip | Quota | Stake | EV |
|---|-------|-----|-------|-------|-----|
| 1 | Paris FC vs Angers | 2 | 4.61 | €2.41 | +34% |
| 2 | Alaves vs Betis | 2 | 2.82 | €4.20 | +30% |
| 3 | Arsenal vs Man Utd | 2 | 5.48 | €1.52 | +27% |
| 4 | **Brentford vs Forest** | **1** | **1.84** | **€7.86** | +26% |
| 5 | Palace vs Chelsea | 1 | 3.46 | €2.62 | +25% |
| 6 | Sociedad vs Celta | 2 | 3.54 | €2.20 | +22% |
| 7 | Genoa vs Bologna | 1 | 3.28 | €1.99 | +18% |
| 8 | Lille vs Strasbourg | 1 | 2.40 | €1.56 | +8.7% |

**Note**: Il modello v1.1 è molto più bilanciato. Abbiamo rimosso le scommesse "folli" (es. Mallorca @ 9.73) impostando un limite di quota a 6.0 e corretto la formula della forza difensiva.

---

## 🎯 Strategia v1.1

| Parametro | Valore |
|-----------|--------|
| Min EV | 5% |
| Min Edge | 3% |
| Kelly Fraction | 25% |
| Max Single | 10% |
| Max Daily | 25% |
| **Max Odds** | **6.0** |

---

## 🧠 Learnings

### Settimana 1
- **Day 1**: Trovato bug nel calcolo xG (i fattori difensivi erano invertiti). Corretto in v1.1. Ora le scommesse sono più distribuite e meno dipendenti da outlier statistici.
