"""
ADVANCED VALUE BETTING ENGINE v2
================================

Sistema COMPLETO che:
1. Scarica dati AVANZATI da Understat (xG, form, stats)
2. Scarica QUOTE REALI da Oddsportal
3. Calcola Expected Value VERO
4. Raccomanda SOLO scommesse con +EV
5. Calcola stake ottimale (Kelly Criterion)

Usage:
    python value_bets.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import numpy as np
from scipy.stats import poisson
import time
import sys
sys.path.insert(0, '.')

from src.ingestion.odds_scraper import OddsportalScraper


class AdvancedDataScraper:
    """Scarica dati avanzati da Understat."""
    
    LEAGUES = {
        'Serie A': 'https://understat.com/league/Serie_A',
        'Premier League': 'https://understat.com/league/EPL',
        'La Liga': 'https://understat.com/league/La_Liga',
        'Bundesliga': 'https://understat.com/league/Bundesliga',
        'Ligue 1': 'https://understat.com/league/Ligue_1',
    }
    
    def __init__(self, driver):
        self.driver = driver
        self.teams_data = {}
    
    def load_league(self, league: str) -> dict:
        url = self.LEAGUES.get(league)
        if not url:
            return {}
        
        try:
            self.driver.get(url)
            time.sleep(2)
            
            matches = self.driver.execute_script('return window.datesData;') or []
            teams = self.driver.execute_script('return window.teamsData;') or {}
            
            return {'matches': matches, 'teams': teams}
        except Exception as e:
            return {}
    
    def calculate_advanced_stats(self, matches: list, teams: dict, league: str):
        for team_id, team_info in teams.items():
            team_name = team_info.get('title', f'Team_{team_id}')
            history = team_info.get('history', [])
            
            if len(history) < 3:
                continue
            
            xg_list = [float(h.get('xG', 0)) for h in history]
            xga_list = [float(h.get('xGA', 0)) for h in history]
            goals_list = [int(h.get('scored', 0)) for h in history]
            
            recent_5 = history[-5:] if len(history) >= 5 else history
            recent_xg = np.mean([float(h.get('xG', 0)) for h in recent_5])
            recent_xga = np.mean([float(h.get('xGA', 0)) for h in recent_5])
            
            self.teams_data[(league, team_name)] = {
                'matches': len(history),
                'xg_per_90': sum(xg_list) / len(history),
                'xga_per_90': sum(xga_list) / len(history),
                'goals_per_90': sum(goals_list) / len(history),
                'form_xg': recent_xg,
                'form_xga': recent_xga,
            }


class ValueBettingEngine:
    """Motore Value Betting con quote REALI."""
    
    HOME_ADVANTAGE = 1.12
    
    def __init__(self):
        self.driver = None
        self.data_scraper = None
        self.odds_scraper = None
        self.real_odds = {}
        
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
            self.data_scraper = AdvancedDataScraper(self.driver)
        return self.driver
    
    def _cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def predict_match(self, home: str, away: str, league: str) -> dict:
        h_stats = self.data_scraper.teams_data.get((league, home))
        a_stats = self.data_scraper.teams_data.get((league, away))
        
        if not h_stats or not a_stats:
            return None
        
        # xG atteso con pesi diversi
        h_def_quality = a_stats['xga_per_90'] / 1.3
        a_def_quality = h_stats['xga_per_90'] / 1.3
        
        home_expected = (
            0.5 * h_stats['xg_per_90'] * h_def_quality +
            0.3 * h_stats['form_xg'] * h_def_quality +
            0.2 * h_stats['goals_per_90']
        ) * self.HOME_ADVANTAGE
        
        away_expected = (
            0.5 * a_stats['xg_per_90'] * a_def_quality +
            0.3 * a_stats['form_xg'] * a_def_quality +
            0.2 * a_stats['goals_per_90']
        )
        
        # Poisson
        max_goals = 8
        h_probs = poisson.pmf(range(max_goals), home_expected)
        a_probs = poisson.pmf(range(max_goals), away_expected)
        matrix = np.outer(h_probs, a_probs)
        
        home_win = np.sum(np.tril(matrix, -1))
        draw = np.sum(np.diag(matrix))
        away_win = np.sum(np.triu(matrix, 1))
        over_25 = 1 - sum(matrix[i, j] for i in range(3) for j in range(3-i))
        btts = 1 - sum(matrix[0, :]) - sum(matrix[:, 0]) + matrix[0, 0]
        
        return {
            'home_xg': home_expected,
            'away_xg': away_expected,
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'over_25': over_25,
            'btts': btts,
        }

    def calculate_ev(self, prob: float, odds: float) -> float:
        """EV = (prob * (odds - 1)) - (1 - prob)"""
        return (prob * (odds - 1)) - (1 - prob)
    
    def calculate_kelly(self, prob: float, odds: float, bankroll: float = 100) -> float:
        """Kelly Criterion (quarter Kelly per sicurezza)."""
        b = odds - 1
        q = 1 - prob
        kelly = (b * prob - q) / b if b > 0 else 0
        
        if kelly <= 0:
            return 0
        
        kelly = kelly * 0.25  # Quarter Kelly
        kelly = min(kelly, 0.10)  # Max 10%
        return kelly * bankroll

    def find_match_odds(self, home: str, away: str, league: str) -> dict:
        """Trova le quote reali per una partita."""
        league_odds = self.real_odds.get(league, [])
        
        home_lower = home.lower()
        away_lower = away.lower()
        
        for match in league_odds:
            m_home = match.get('home', '').lower()
            m_away = match.get('away', '').lower()
            
            # Fuzzy match
            home_match = any(w in m_home for w in home_lower.split()) or any(w in home_lower for w in m_home.split())
            away_match = any(w in m_away for w in away_lower.split()) or any(w in away_lower for w in m_away.split())
            
            if home_match and away_match:
                return {
                    '1': match.get('odds_1'),
                    'X': match.get('odds_x'),
                    '2': match.get('odds_2'),
                    'bookmaker_home': match.get('home'),
                    'bookmaker_away': match.get('away'),
                }
        
        return None

    def get_value_bets(self, pred: dict, odds: dict, home: str, away: str) -> list:
        """Identifica scommesse con EV positivo usando quote REALI."""
        value_bets = []
        
        markets = [
            ('1', pred['home_win'], odds.get('1'), f"Vittoria {home}"),
            ('X', pred['draw'], odds.get('X'), "Pareggio"),
            ('2', pred['away_win'], odds.get('2'), f"Vittoria {away}"),
        ]
        
        for market, prob, real_odds, description in markets:
            if not real_odds or real_odds <= 1:
                continue
            
            implied_prob = 1 / real_odds
            ev = self.calculate_ev(prob, real_odds)
            edge = prob - implied_prob
            
            # Solo se abbiamo un vantaggio REALE
            if ev > 0.02 and edge > 0.02:  # EV > 2% e Edge > 2%
                stake = self.calculate_kelly(prob, real_odds)
                
                value_bets.append({
                    'market': market,
                    'description': description,
                    'our_prob': prob,
                    'implied_prob': implied_prob,
                    'odds': real_odds,
                    'ev': ev,
                    'edge': edge,
                    'kelly_stake': stake,
                    'is_real_value': True
                })
        
        value_bets.sort(key=lambda x: x['ev'], reverse=True)
        return value_bets

    def run(self):
        print("\n" + "="*75)
        print("   💰 VALUE BETTING ENGINE v2 - QUOTE REALI")
        print("   Trova scommesse con Expected Value POSITIVO")
        print("="*75)
        
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"\n📅 Data: {today}")
        
        try:
            self._get_driver()
            
            # Step 1: Scarica quote REALI da Oddsportal
            print("\n📊 Step 1: Scaricamento QUOTE REALI da Oddsportal...")
            odds_scraper = OddsportalScraper(self.driver)
            
            for league, url in OddsportalScraper.LEAGUES.items():
                print(f"   → {league}...", end=" ")
                matches = odds_scraper.scrape_league_odds(league)
                self.real_odds[league] = matches
                print(f"OK ({len(matches)} partite)")
                time.sleep(1)
            
            # Step 2: Carica dati avanzati da Understat
            print("\n📊 Step 2: Caricamento dati xG da Understat...")
            
            todays_matches = []
            
            for league in AdvancedDataScraper.LEAGUES.keys():
                print(f"   → {league}...", end=" ")
                data = self.data_scraper.load_league(league)
                
                if data.get('matches') and data.get('teams'):
                    self.data_scraper.calculate_advanced_stats(
                        data['matches'], data['teams'], league
                    )
                    
                    for m in data['matches']:
                        if m.get('datetime', '')[:10] == today and not m.get('isResult'):
                            todays_matches.append({
                                'league': league,
                                'home': m.get('h', {}).get('title'),
                                'away': m.get('a', {}).get('title'),
                                'time': m.get('datetime', '')[11:16],
                            })
                    
                    print(f"OK")
                else:
                    print("SKIP")
            
            if not todays_matches:
                print("\n❌ Nessuna partita trovata per oggi!")
                return
            
            print(f"\n🏟️ {len(todays_matches)} partite da analizzare")
            
            # Step 3: Calcola Value Bets con quote REALI
            print("\n" + "="*75)
            print("   🎯 VALUE BETS CON QUOTE REALI")
            print("="*75)
            
            all_value_bets = []
            matches_with_odds = 0
            
            for m in todays_matches:
                pred = self.predict_match(m['home'], m['away'], m['league'])
                if not pred:
                    continue
                
                # Trova quote REALI
                real_odds = self.find_match_odds(m['home'], m['away'], m['league'])
                
                if not real_odds:
                    continue
                
                matches_with_odds += 1
                value_bets = self.get_value_bets(pred, real_odds, m['home'], m['away'])
                
                if value_bets:
                    for vb in value_bets:
                        all_value_bets.append({
                            'match': m,
                            'prediction': pred,
                            'bookmaker_match': f"{real_odds.get('bookmaker_home')} vs {real_odds.get('bookmaker_away')}",
                            **vb
                        })
            
            print(f"\n📈 Partite con quote trovate: {matches_with_odds}/{len(todays_matches)}")
            
            if not all_value_bets:
                print("\n⚠️ NESSUN VALUE BET TROVATO!")
                print("   Le quote dei bookmaker sono corrette - nessun vantaggio identificato.")
                print("   Questo è NORMALE - i bookmaker sono molto accurati.")
                return
            
            # Ordina per EV
            all_value_bets.sort(key=lambda x: x['ev'], reverse=True)
            
            # Output
            print(f"\n🔥 TROVATI {len(all_value_bets)} VALUE BETS!")
            
            for i, bet in enumerate(all_value_bets[:10], 1):
                m = bet['match']
                ev_pct = bet['ev'] * 100
                edge_pct = bet['edge'] * 100
                
                if ev_pct > 15:
                    emoji = "🔥🔥🔥"
                elif ev_pct > 10:
                    emoji = "🔥🔥"
                elif ev_pct > 5:
                    emoji = "🔥"
                else:
                    emoji = "✅"
                
                print(f"\n{emoji} #{i} | {m['league']} - {m['time']}")
                print(f"   {m['home']} vs {m['away']}")
                print(f"   Quote reali: 1={bet.get('odds', 0):.2f}")
                print(f"   ┣━ Scommessa: {bet['description']}")
                print(f"   ┣━ Nostra Prob: {bet['our_prob']:.1%}")
                print(f"   ┣━ Prob Bookmaker: {bet['implied_prob']:.1%}")
                print(f"   ┣━ 📊 EDGE: +{edge_pct:.1f}%")
                print(f"   ┣━ 💰 EV: +{ev_pct:.1f}%")
                print(f"   ┗━ 💵 Stake (€100 bank): €{bet['kelly_stake']:.2f}")
            
            # Riepilogo finale
            print("\n" + "="*75)
            print("   🏆 RIEPILOGO - MIGLIORI VALUE BETS")
            print("="*75)
            
            total_stake = sum(b['kelly_stake'] for b in all_value_bets[:5])
            avg_ev = np.mean([b['ev'] for b in all_value_bets[:5]]) if all_value_bets else 0
            
            for i, bet in enumerate(all_value_bets[:5], 1):
                m = bet['match']
                print(f"\n   {i}. {m['home']} vs {m['away']}")
                print(f"      {bet['description']} @ {bet['odds']:.2f}")
                print(f"      EV: +{bet['ev']*100:.1f}% | Edge: +{bet['edge']*100:.1f}%")
                print(f"      Stake: €{bet['kelly_stake']:.2f}")
            
            if all_value_bets:
                print(f"\n   📊 Stake totale: €{total_stake:.2f}")
                print(f"   📊 EV medio: +{avg_ev*100:.1f}%")
                print(f"   📊 ROI atteso: +{avg_ev*100:.1f}% sul lungo periodo")
            
            print("\n" + "="*75)
            print("   ✅ QUESTE SONO SCOMMESSE CON VALUE REALE!")
            print("   📌 Le quote sono state prese da Oddsportal")
            print("="*75)
            
        finally:
            self._cleanup()


if __name__ == "__main__":
    engine = ValueBettingEngine()
    engine.run()
