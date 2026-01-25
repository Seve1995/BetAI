"""
DAILY BETTING EXPERIMENT RUNNER
===============================

Esegui questo script ogni giorno per:
1. Controllare i risultati delle scommesse del giorno precedente
2. Aggiornare il bankroll
3. Analizzare le partite di oggi
4. Piazzare nuove scommesse
5. Salvare lo stato per il giorno successivo

Usage:
    python run_experiment.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import poisson
import json
import os
import time
import sys

sys.path.insert(0, '.')
from src.ingestion.odds_scraper import OddsportalScraper


class ExperimentRunner:
    """
    Gestisce l'esperimento di betting giornaliero.
    Tiene traccia del bankroll, scommesse, e impara dagli errori.
    """
    
    STATE_FILE = "experiment_state.json"
    EXPERIMENT_DOC = "EXPERIMENT.md"
    
    LEAGUES = {
        'Serie A': 'https://understat.com/league/Serie_A',
        'Premier League': 'https://understat.com/league/EPL',
        'La Liga': 'https://understat.com/league/La_Liga',
        'Bundesliga': 'https://understat.com/league/Bundesliga',
        'Ligue 1': 'https://understat.com/league/Ligue_1',
    }
    
    def __init__(self):
        self.state = self.load_state()
        self.driver = None
        self.teams_data = {}
        self.real_odds = {}
        
    def load_state(self) -> dict:
        """Carica lo stato persistente."""
        if os.path.exists(self.STATE_FILE):
            with open(self.STATE_FILE, 'r') as f:
                return json.load(f)
        else:
            # Stato iniziale
            return {
                "experiment": {
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d"),
                    "initial_bankroll": 100.0
                },
                "current_state": {
                    "bankroll": 100.0,
                    "day": 1,
                    "last_run": None
                },
                "strategy": {
                    "version": "1.0",
                    "min_ev": 0.05,
                    "min_edge": 0.03,
                    "kelly_fraction": 0.25,
                    "max_single_stake_pct": 0.10,
                    "max_daily_stake_pct": 0.25
                },
                "stats": {
                    "total_bets": 0,
                    "wins": 0,
                    "losses": 0,
                    "pending": 0,
                    "total_staked": 0.0,
                    "total_returns": 0.0,
                    "total_profit": 0.0
                },
                "pending_bets": [],
                "completed_bets": [],
                "learnings": []
            }
    
    def save_state(self):
        """Salva lo stato persistente."""
        with open(self.STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def _get_driver(self):
        if self.driver is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            self.driver = webdriver.Chrome(options=options)
        return self.driver
    
    def _cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def check_pending_bets(self):
        """
        Controlla i risultati delle scommesse pendenti.
        Per ora chiede all'utente di inserire i risultati.
        """
        pending = self.state.get("pending_bets", [])
        
        if not pending:
            return
        
        print("\n" + "="*60)
        print("   📋 CONTROLLO SCOMMESSE PENDENTI")
        print("="*60)
        
        still_pending = []
        
        for bet in pending:
            print(f"\n   {bet['match']}")
            print(f"   Tip: {bet['tip']} @ {bet['odds']:.2f}")
            print(f"   Stake: €{bet['stake']:.2f}")
            print(f"   Data: {bet['date']}")
            
            result = input("   Risultato (W=vinta, L=persa, P=pendente): ").strip().upper()
            
            if result == 'W':
                profit = bet['stake'] * (bet['odds'] - 1)
                self.state['current_state']['bankroll'] += profit + bet['stake']
                self.state['stats']['wins'] += 1
                self.state['stats']['total_returns'] += profit + bet['stake']
                self.state['stats']['total_profit'] += profit
                bet['result'] = 'WIN'
                bet['profit'] = profit
                self.state['completed_bets'].append(bet)
                print(f"   ✅ VINTA! +€{profit:.2f}")
                
            elif result == 'L':
                self.state['stats']['losses'] += 1
                self.state['stats']['total_profit'] -= bet['stake']
                bet['result'] = 'LOSS'
                bet['profit'] = -bet['stake']
                self.state['completed_bets'].append(bet)
                print(f"   ❌ PERSA! -€{bet['stake']:.2f}")
                
            else:
                still_pending.append(bet)
                print("   ⏳ Ancora pendente")
        
        self.state['pending_bets'] = still_pending
        self.state['stats']['pending'] = len(still_pending)
        
        print(f"\n   Bankroll aggiornato: €{self.state['current_state']['bankroll']:.2f}")
    
    def load_xg_data(self, league: str) -> dict:
        """Carica dati xG da Understat."""
        url = self.LEAGUES.get(league)
        if not url:
            return {}
        
        try:
            driver = self._get_driver()
            driver.get(url)
            time.sleep(2)
            
            matches = driver.execute_script('return window.datesData;') or []
            teams = driver.execute_script('return window.teamsData;') or {}
            
            return {'matches': matches, 'teams': teams}
        except:
            return {}
    
    def calculate_team_stats(self, teams: dict, league: str):
        """Calcola statistiche squadre."""
        for team_id, team_info in teams.items():
            team_name = team_info.get('title', f'Team_{team_id}')
            history = team_info.get('history', [])
            
            if len(history) < 3:
                continue
            
            xg_list = [float(h.get('xG', 0)) for h in history]
            xga_list = [float(h.get('xGA', 0)) for h in history]
            goals_list = [int(h.get('scored', 0)) for h in history]
            
            recent_5 = history[-5:] if len(history) >= 5 else history
            
            self.teams_data[(league, team_name)] = {
                'xg_per_90': sum(xg_list) / len(history),
                'xga_per_90': sum(xga_list) / len(history),
                'goals_per_90': sum(goals_list) / len(history),
                'form_xg': np.mean([float(h.get('xG', 0)) for h in recent_5]),
            }
    
    def predict_match(self, home: str, away: str, league: str) -> dict:
        """Predizione usando modello Poisson."""
        h_stats = self.teams_data.get((league, home))
        a_stats = self.teams_data.get((league, away))
        
        if not h_stats or not a_stats:
            return None
        
        home_advantage = 1.12
        h_def = a_stats['xga_per_90'] / 1.3
        a_def = h_stats['xga_per_90'] / 1.3
        
        home_xg = (0.5 * h_stats['xg_per_90'] * h_def + 
                   0.3 * h_stats['form_xg'] * h_def +
                   0.2 * h_stats['goals_per_90']) * home_advantage
        
        away_xg = (0.5 * a_stats['xg_per_90'] * a_def +
                   0.3 * a_stats['form_xg'] * a_def +
                   0.2 * a_stats['goals_per_90'])
        
        h_probs = poisson.pmf(range(8), home_xg)
        a_probs = poisson.pmf(range(8), away_xg)
        matrix = np.outer(h_probs, a_probs)
        
        return {
            'home_win': np.sum(np.tril(matrix, -1)),
            'draw': np.sum(np.diag(matrix)),
            'away_win': np.sum(np.triu(matrix, 1)),
            'home_xg': home_xg,
            'away_xg': away_xg,
        }
    
    def find_value_bets(self, todays_matches: list) -> list:
        """Trova value bets per oggi."""
        strategy = self.state['strategy']
        bankroll = self.state['current_state']['bankroll']
        
        value_bets = []
        
        for m in todays_matches:
            pred = self.predict_match(m['home'], m['away'], m['league'])
            if not pred:
                continue
            
            # Trova quote
            odds = self.find_match_odds(m['home'], m['away'], m['league'])
            if not odds:
                continue
            
            markets = [
                ('1', pred['home_win'], odds.get('1'), f"1 ({m['home']})"),
                ('X', pred['draw'], odds.get('X'), "X"),
                ('2', pred['away_win'], odds.get('2'), f"2 ({m['away']})"),
            ]
            
            for market, prob, real_odds, tip in markets:
                if not real_odds or real_odds <= 1:
                    continue
                
                implied = 1 / real_odds
                ev = (prob * (real_odds - 1)) - (1 - prob)
                edge = prob - implied
                
                if ev >= strategy['min_ev'] and edge >= strategy['min_edge']:
                    # Kelly stake
                    kelly = ((real_odds - 1) * prob - (1 - prob)) / (real_odds - 1)
                    kelly = kelly * strategy['kelly_fraction']
                    kelly = max(0, min(kelly, strategy['max_single_stake_pct']))
                    stake = kelly * bankroll
                    
                    if stake > 0.5:  # Min €0.50
                        value_bets.append({
                            'match': f"{m['home']} vs {m['away']}",
                            'league': m['league'],
                            'time': m['time'],
                            'tip': tip,
                            'odds': real_odds,
                            'our_prob': prob,
                            'implied_prob': implied,
                            'ev': ev,
                            'edge': edge,
                            'stake': round(stake, 2),
                        })
        
        # Ordina per EV e limita stake totale
        value_bets.sort(key=lambda x: x['ev'], reverse=True)
        
        max_daily = bankroll * strategy['max_daily_stake_pct']
        total_stake = 0
        selected = []
        
        for bet in value_bets:
            if total_stake + bet['stake'] <= max_daily:
                selected.append(bet)
                total_stake += bet['stake']
        
        return selected
    
    def find_match_odds(self, home: str, away: str, league: str) -> dict:
        """Trova quote reali."""
        league_odds = self.real_odds.get(league, [])
        
        home_lower = home.lower()
        away_lower = away.lower()
        
        for match in league_odds:
            m_home = match.get('home', '').lower()
            m_away = match.get('away', '').lower()
            
            if any(w in m_home for w in home_lower.split()) and \
               any(w in m_away for w in away_lower.split()):
                return {
                    '1': match.get('odds_1'),
                    'X': match.get('odds_x'),
                    '2': match.get('odds_2'),
                }
        return None
    
    def place_bets(self, bets: list):
        """Registra le scommesse."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        for bet in bets:
            bet_record = {
                'date': today,
                'match': bet['match'],
                'league': bet['league'],
                'tip': bet['tip'],
                'odds': bet['odds'],
                'stake': bet['stake'],
                'ev': bet['ev'],
                'edge': bet['edge'],
                'our_prob': bet['our_prob'],
                'result': 'PENDING'
            }
            
            self.state['pending_bets'].append(bet_record)
            self.state['stats']['total_bets'] += 1
            self.state['stats']['pending'] += 1
            self.state['stats']['total_staked'] += bet['stake']
            self.state['current_state']['bankroll'] -= bet['stake']
    
    def update_experiment_doc(self, bets: list):
        """Aggiorna il documento dell'esperimento."""
        today = datetime.now().strftime("%Y-%m-%d")
        day_num = self.state['current_state']['day']
        bankroll = self.state['current_state']['bankroll']
        stats = self.state['stats']
        
        # Leggi documento esistente
        with open(self.EXPERIMENT_DOC, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Aggiorna stato attuale
        roi = (stats['total_profit'] / max(stats['total_staked'], 1)) * 100
        
        new_state = f"""## 📊 Stato Attuale

| Metrica | Valore |
|---------|--------|
| **Bankroll** | €{bankroll:.2f} |
| **Giorno** | {day_num}/31 |
| **Scommesse Totali** | {stats['total_bets']} |
| **Vinte** | {stats['wins']} |
| **Perse** | {stats['losses']} |
| **ROI** | {roi:.1f}% |"""
        
        # Sostituisci lo stato
        import re
        content = re.sub(r'## 📊 Stato Attuale.*?(?=\n---)', new_state + '\n', content, flags=re.DOTALL)
        
        # Aggiungi entry per oggi
        if bets:
            bets_text = "\n".join([
                f"- {b['tip']} @ {b['odds']:.2f} | Stake: €{b['stake']:.2f} | EV: +{b['ev']*100:.1f}%"
                for b in bets
            ])
        else:
            bets_text = "*Nessuna scommessa piazzata*"
        
        day_entry = f"""### Giorno {day_num} - {today}
**Bankroll**: €{bankroll:.2f}

#### Scommesse del Giorno
{bets_text}

---

"""
        
        # Inserisci dopo "## 📈 Cronologia Giornaliera"
        if f"### Giorno {day_num}" not in content:
            content = content.replace("## 📈 Cronologia Giornaliera\n\n", 
                                     f"## 📈 Cronologia Giornaliera\n\n{day_entry}")
        
        with open(self.EXPERIMENT_DOC, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def analyze_performance(self):
        """Analizza performance e suggerisce miglioramenti."""
        stats = self.state['stats']
        completed = self.state['completed_bets']
        
        if len(completed) < 5:
            return None
        
        # Calcola metriche
        win_rate = stats['wins'] / max(len(completed), 1)
        avg_ev_won = np.mean([b['ev'] for b in completed if b['result'] == 'WIN']) if stats['wins'] > 0 else 0
        avg_ev_lost = np.mean([b['ev'] for b in completed if b['result'] == 'LOSS']) if stats['losses'] > 0 else 0
        
        # Suggerimenti basati sui dati
        suggestions = []
        
        if win_rate < 0.35 and stats['losses'] >= 5:
            suggestions.append("Win rate basso. Considerare aumentare la soglia EV minima.")
        
        if avg_ev_lost > avg_ev_won and stats['losses'] > stats['wins']:
            suggestions.append("Perdite su scommesse ad alto EV. Verificare accuratezza modello.")
        
        return {
            'win_rate': win_rate,
            'avg_ev_won': avg_ev_won,
            'avg_ev_lost': avg_ev_lost,
            'suggestions': suggestions
        }
    
    def run(self):
        """Esegue l'esperimento giornaliero."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        print("\n" + "="*70)
        print("   🎰 BETTING EXPERIMENT - ESECUZIONE GIORNALIERA")
        print("="*70)
        print(f"\n📅 Data: {today}")
        print(f"💰 Bankroll: €{self.state['current_state']['bankroll']:.2f}")
        print(f"📊 Giorno: {self.state['current_state']['day']}/31")
        
        try:
            # Step 1: Controlla scommesse pendenti
            self.check_pending_bets()
            
            # Step 2: Carica quote reali
            print("\n📊 Caricamento quote da Oddsportal...")
            self._get_driver()
            odds_scraper = OddsportalScraper(self.driver)
            
            for league in self.LEAGUES.keys():
                print(f"   → {league}...", end=" ")
                matches = odds_scraper.scrape_league_odds(league)
                self.real_odds[league] = matches
                print(f"OK ({len(matches)} partite)")
                time.sleep(1)
            
            # Step 3: Carica dati xG
            print("\n📊 Caricamento dati xG da Understat...")
            todays_matches = []
            
            for league in self.LEAGUES.keys():
                print(f"   → {league}...", end=" ")
                data = self.load_xg_data(league)
                
                if data.get('teams'):
                    self.calculate_team_stats(data['teams'], league)
                    
                    for m in data.get('matches', []):
                        if m.get('datetime', '')[:10] == today and not m.get('isResult'):
                            todays_matches.append({
                                'league': league,
                                'home': m.get('h', {}).get('title'),
                                'away': m.get('a', {}).get('title'),
                                'time': m.get('datetime', '')[11:16],
                            })
                    print("OK")
                else:
                    print("SKIP")
            
            print(f"\n🏟️ {len(todays_matches)} partite da analizzare")
            
            # Step 4: Trova value bets
            value_bets = self.find_value_bets(todays_matches)
            
            if not value_bets:
                print("\n⚠️ Nessun value bet trovato oggi!")
                print("   Il modello non trova scommesse con EV positivo.")
            else:
                print(f"\n🔥 Trovati {len(value_bets)} VALUE BETS!")
                
                total_stake = sum(b['stake'] for b in value_bets)
                
                for i, bet in enumerate(value_bets, 1):
                    print(f"\n   #{i} {bet['match']}")
                    print(f"      {bet['tip']} @ {bet['odds']:.2f}")
                    print(f"      EV: +{bet['ev']*100:.1f}% | Edge: +{bet['edge']*100:.1f}%")
                    print(f"      Stake: €{bet['stake']:.2f}")
                
                print(f"\n   💰 Stake totale: €{total_stake:.2f}")
                
                # Chiedi conferma
                confirm = input("\n   Piazzare queste scommesse? (s/n): ").strip().lower()
                
                if confirm == 's':
                    self.place_bets(value_bets)
                    print(f"\n   ✅ {len(value_bets)} scommesse piazzate!")
                    print(f"   💰 Nuovo bankroll: €{self.state['current_state']['bankroll']:.2f}")
                else:
                    print("\n   ❌ Scommesse annullate.")
                    value_bets = []
            
            # Step 5: Analizza performance
            analysis = self.analyze_performance()
            if analysis and analysis['suggestions']:
                print("\n📈 Analisi Performance:")
                for s in analysis['suggestions']:
                    print(f"   💡 {s}")
            
            # Step 6: Aggiorna stato
            self.state['current_state']['last_run'] = today
            self.state['current_state']['day'] += 1
            
            # Salva tutto
            self.save_state()
            self.update_experiment_doc(value_bets)
            
            print("\n" + "="*70)
            print(f"   ✅ Esperimento aggiornato! Bankroll: €{self.state['current_state']['bankroll']:.2f}")
            print("="*70)
            
        finally:
            self._cleanup()


if __name__ == "__main__":
    runner = ExperimentRunner()
    runner.run()
