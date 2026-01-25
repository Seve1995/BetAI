"""
BETTING PREDICTION ENGINE - BEST BETS TODAY
============================================

Esegui questo script per ottenere automaticamente le migliori scommesse di oggi.

Usage:
    python predict_today.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import numpy as np
from scipy.stats import poisson
import time


class BettingPredictor:
    """
    Sistema completo per predire le partite di oggi e identificare value bets.
    Usa i dati xG storici scaricati direttamente da Understat.
    """
    
    LEAGUES = {
        'Serie A': 'https://understat.com/league/Serie_A',
        'Premier League': 'https://understat.com/league/EPL',
        'La Liga': 'https://understat.com/league/La_Liga',
        'Bundesliga': 'https://understat.com/league/Bundesliga',
        'Ligue 1': 'https://understat.com/league/Ligue_1',
    }
    
    # Moltiplicatori medi per conversione odds -> probabilita
    HOME_ADVANTAGE = 1.15  # Fattore casa

    def __init__(self):
        self.driver = None
        self.all_matches = {}  # Storico partite per lega
        self.team_stats = {}   # Statistiche squadre
        
    def _get_driver(self):
        if self.driver is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')
            self.driver = webdriver.Chrome(options=options)
        return self.driver
    
    def _cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def load_league_data(self, league_name: str) -> list:
        """Scarica tutti i dati storici di una lega da Understat."""
        url = self.LEAGUES.get(league_name)
        if not url:
            return []
        
        try:
            driver = self._get_driver()
            driver.get(url)
            time.sleep(2)
            
            dates_data = driver.execute_script('return window.datesData;')
            return dates_data if dates_data else []
        except Exception as e:
            print(f"   Errore {league_name}: {e}")
            return []

    def calculate_team_stats(self, matches: list, league: str):
        """
        Calcola statistiche medie per ogni squadra basate sui dati xG.
        """
        team_data = {}
        
        for m in matches:
            if not m.get('isResult'):  # Solo partite finite
                continue
                
            home = m.get('h', {}).get('title')
            away = m.get('a', {}).get('title')
            
            try:
                home_xg = float(m.get('xG', {}).get('h', 0) or 0)
                away_xg = float(m.get('xG', {}).get('a', 0) or 0)
            except:
                continue
            
            # Inizializza se non esiste
            for team in [home, away]:
                if team not in team_data:
                    team_data[team] = {
                        'xg_for': [], 'xg_against': [],
                        'goals_for': [], 'goals_against': [],
                        'home_matches': 0, 'away_matches': 0
                    }
            
            # Casa
            team_data[home]['xg_for'].append(home_xg)
            team_data[home]['xg_against'].append(away_xg)
            team_data[home]['goals_for'].append(int(m.get('goals', {}).get('h', 0) or 0))
            team_data[home]['goals_against'].append(int(m.get('goals', {}).get('a', 0) or 0))
            team_data[home]['home_matches'] += 1
            
            # Trasferta
            team_data[away]['xg_for'].append(away_xg)
            team_data[away]['xg_against'].append(home_xg)
            team_data[away]['goals_for'].append(int(m.get('goals', {}).get('a', 0) or 0))
            team_data[away]['goals_against'].append(int(m.get('goals', {}).get('h', 0) or 0))
            team_data[away]['away_matches'] += 1
        
        # Calcola medie
        for team, data in team_data.items():
            if len(data['xg_for']) >= 3:  # Minimo 3 partite
                self.team_stats[(league, team)] = {
                    'attack': np.mean(data['xg_for']),
                    'defense': np.mean(data['xg_against']),
                    'matches': len(data['xg_for']),
                }

    def predict_match(self, home: str, away: str, league: str) -> dict:
        """
        Predice il risultato di una partita usando il modello Poisson.
        """
        home_stats = self.team_stats.get((league, home))
        away_stats = self.team_stats.get((league, away))
        
        if not home_stats or not away_stats:
            return None
        
        # Expected goals (con vantaggio casa)
        home_xg = home_stats['attack'] * (away_stats['defense'] / 1.3) * self.HOME_ADVANTAGE
        away_xg = away_stats['attack'] * (home_stats['defense'] / 1.3)
        
        # Distribuzione Poisson per i gol
        max_goals = 7
        home_probs = poisson.pmf(range(max_goals), home_xg)
        away_probs = poisson.pmf(range(max_goals), away_xg)
        
        # Matrice dei risultati
        matrix = np.outer(home_probs, away_probs)
        
        # Probabilita 1X2
        home_win = np.sum(np.tril(matrix, -1))
        draw = np.sum(np.diag(matrix))
        away_win = np.sum(np.triu(matrix, 1))
        
        # Over/Under 2.5
        over_25 = 1 - sum(matrix[i, j] for i in range(3) for j in range(3-i))
        
        # BTTS (Both Teams To Score)
        btts_yes = 1 - sum(matrix[0, :]) - sum(matrix[:, 0]) + matrix[0, 0]
        
        return {
            'home_xg': home_xg,
            'away_xg': away_xg,
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'over_25': over_25,
            'btts': btts_yes,
            'home_data': home_stats,
            'away_data': away_stats,
        }

    def get_best_bet(self, pred: dict, home: str, away: str) -> dict:
        """
        Identifica la scommessa migliore per la partita.
        Restituisce il tip con la confidence piu alta.
        """
        bets = []
        
        # 1X2
        if pred['home_win'] > 0.55:
            bets.append({
                'tip': f"1 (Vittoria {home})",
                'prob': pred['home_win'],
                'confidence': 'ALTA' if pred['home_win'] > 0.65 else 'MEDIA'
            })
        if pred['away_win'] > 0.45:
            bets.append({
                'tip': f"2 (Vittoria {away})",
                'prob': pred['away_win'],
                'confidence': 'ALTA' if pred['away_win'] > 0.55 else 'MEDIA'
            })
        if pred['draw'] > 0.30 and pred['home_win'] < 0.45 and pred['away_win'] < 0.40:
            bets.append({
                'tip': "X (Pareggio)",
                'prob': pred['draw'],
                'confidence': 'MEDIA'
            })
        
        # Over/Under
        if pred['over_25'] > 0.60:
            bets.append({
                'tip': "Over 2.5",
                'prob': pred['over_25'],
                'confidence': 'ALTA' if pred['over_25'] > 0.70 else 'MEDIA'
            })
        elif pred['over_25'] < 0.40:
            bets.append({
                'tip': "Under 2.5",
                'prob': 1 - pred['over_25'],
                'confidence': 'ALTA' if pred['over_25'] < 0.30 else 'MEDIA'
            })
        
        # BTTS
        if pred['btts'] > 0.65:
            bets.append({
                'tip': "Gol (BTTS Si)",
                'prob': pred['btts'],
                'confidence': 'ALTA' if pred['btts'] > 0.75 else 'MEDIA'
            })
        elif pred['btts'] < 0.35:
            bets.append({
                'tip': "No Gol (BTTS No)",
                'prob': 1 - pred['btts'],
                'confidence': 'MEDIA'
            })
        
        # Ordina per probabilita
        bets.sort(key=lambda x: x['prob'], reverse=True)
        return bets[0] if bets else None

    def run(self):
        """
        Esegue l'intero processo di predizione.
        """
        print("\n" + "="*70)
        print("   BETTING PREDICTION ENGINE - MIGLIORI SCOMMESSE DI OGGI")
        print("="*70)
        
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"\n📅 Data: {today}")
        print("-"*70)
        
        todays_matches = []
        
        try:
            # Step 1: Scarica dati e calcola statistiche
            print("\n📊 Caricamento dati storici da Understat...")
            for league in self.LEAGUES.keys():
                print(f"   → {league}...", end=" ")
                matches = self.load_league_data(league)
                
                if matches:
                    self.all_matches[league] = matches
                    self.calculate_team_stats(matches, league)
                    
                    # Trova partite di oggi
                    for m in matches:
                        if m.get('datetime', '')[:10] == today:
                            todays_matches.append({
                                'league': league,
                                'home': m.get('h', {}).get('title'),
                                'away': m.get('a', {}).get('title'),
                                'time': m.get('datetime', '')[11:16],
                                'is_finished': m.get('isResult', False)
                            })
                    
                    team_count = len([k for k in self.team_stats if k[0] == league])
                    print(f"OK ({team_count} squadre)")
                else:
                    print("ERRORE")
            
            if not todays_matches:
                print("\n❌ Nessuna partita trovata per oggi!")
                return
            
            # Filtra solo partite non ancora giocate
            upcoming = [m for m in todays_matches if not m['is_finished']]
            
            print(f"\n🏟️ Trovate {len(todays_matches)} partite oggi ({len(upcoming)} da giocare)")
            
            # Step 2: Genera predizioni
            print("\n" + "="*70)
            print("   🎯 MIGLIORI SCOMMESSE DI OGGI")
            print("="*70)
            
            all_bets = []
            
            for m in upcoming:
                pred = self.predict_match(m['home'], m['away'], m['league'])
                
                if pred:
                    best_bet = self.get_best_bet(pred, m['home'], m['away'])
                    if best_bet:
                        all_bets.append({
                            'match': m,
                            'prediction': pred,
                            'bet': best_bet
                        })
            
            if not all_bets:
                print("\n⚠️ Nessuna scommessa affidabile identificata.")
                return
            
            # Ordina per confidence e probabilita
            all_bets.sort(key=lambda x: (
                x['bet']['confidence'] == 'ALTA',
                x['bet']['prob']
            ), reverse=True)
            
            # Output risultati
            print()
            for i, bet in enumerate(all_bets, 1):
                m = bet['match']
                p = bet['prediction']
                b = bet['bet']
                
                conf_emoji = "🔥" if b['confidence'] == 'ALTA' else "⚡"
                
                print(f"\n{conf_emoji} #{i} | {m['league']} - {m['time']}")
                print(f"   {m['home']} vs {m['away']}")
                print(f"   xG Attesi: {p['home_xg']:.2f} - {p['away_xg']:.2f}")
                print(f"   1X2: {p['home_win']:.0%} | {p['draw']:.0%} | {p['away_win']:.0%}")
                print(f"   Over 2.5: {p['over_25']:.0%} | BTTS: {p['btts']:.0%}")
                print(f"   ┗━━ 💰 TIP: {b['tip']} ({b['prob']:.0%}) [{b['confidence']}]")
            
            # Riepilogo TOP 3
            print("\n" + "="*70)
            print("   🏆 TOP 3 SCOMMESSE DEL GIORNO")
            print("="*70)
            
            for i, bet in enumerate(all_bets[:3], 1):
                m = bet['match']
                b = bet['bet']
                print(f"\n   {i}. {m['home']} vs {m['away']}")
                print(f"      ➜ {b['tip']} @ {b['prob']:.0%} confidence")
            
            print("\n" + "="*70)
            
        finally:
            self._cleanup()


if __name__ == "__main__":
    predictor = BettingPredictor()
    predictor.run()
