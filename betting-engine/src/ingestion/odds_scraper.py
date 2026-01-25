"""
ODDS SCRAPER - Scrape quote reali da Oddsportal
================================================

Scarica le quote 1X2, Over/Under, BTTS dai principali bookmaker.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re


class OddsportalScraper:
    """
    Scrape quote live da Oddsportal per tutte le leghe principali.
    """
    
    LEAGUES = {
        'Serie A': 'https://www.oddsportal.com/football/italy/serie-a/',
        'Premier League': 'https://www.oddsportal.com/football/england/premier-league/',
        'La Liga': 'https://www.oddsportal.com/football/spain/laliga/',
        'Bundesliga': 'https://www.oddsportal.com/football/germany/bundesliga/',
        'Ligue 1': 'https://www.oddsportal.com/football/france/ligue-1/',
    }
    
    def __init__(self, driver=None):
        self.driver = driver
        self.own_driver = False
        
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
            self.own_driver = True
        return self.driver
    
    def _cleanup(self):
        if self.own_driver and self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _handle_popups(self):
        """Chiudi eventuali popup (cookie, promo)."""
        try:
            # Cookie consent
            buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button')
            for btn in buttons:
                if 'accept' in btn.text.lower() or 'agree' in btn.text.lower():
                    btn.click()
                    time.sleep(0.5)
                    break
        except:
            pass
    
    def scrape_league_odds(self, league: str) -> list:
        """
        Scarica le quote per tutte le partite di una lega.
        
        Returns:
            List of dicts: [{'home': str, 'away': str, 'odds_1': float, 'odds_x': float, 'odds_2': float, ...}]
        """
        url = self.LEAGUES.get(league)
        if not url:
            return []
        
        try:
            driver = self._get_driver()
            driver.get(url)
            time.sleep(3)
            
            self._handle_popups()
            
            # Esegui JS per estrarre i dati delle partite
            matches_data = driver.execute_script("""
                const matches = [];
                
                // Trova tutte le righe delle partite
                const rows = document.querySelectorAll('div.group.flex');
                
                rows.forEach(row => {
                    try {
                        // Estrai nomi squadre dai link con title
                        const teamLinks = row.querySelectorAll('a[title]');
                        if (teamLinks.length < 2) return;
                        
                        const home = teamLinks[0].getAttribute('title');
                        const away = teamLinks[1].getAttribute('title');
                        
                        // Estrai quote (tutti i numeri decimali nella riga)
                        const allText = row.innerText;
                        const oddsRegex = /\\d+\\.\\d{2}/g;
                        const oddsMatches = allText.match(oddsRegex) || [];
                        
                        // Le prime 3 quote sono 1X2
                        if (oddsMatches.length >= 3) {
                            matches.push({
                                home: home,
                                away: away,
                                odds_1: parseFloat(oddsMatches[0]),
                                odds_x: parseFloat(oddsMatches[1]),
                                odds_2: parseFloat(oddsMatches[2]),
                                raw_text: allText.substring(0, 100)
                            });
                        }
                    } catch (e) {}
                });
                
                return matches;
            """)
            
            return matches_data if matches_data else []
            
        except Exception as e:
            print(f"   Errore scraping {league}: {e}")
            return []
    
    def scrape_all_leagues(self) -> dict:
        """
        Scarica quote per tutte le leghe.
        
        Returns:
            Dict: {'Serie A': [matches...], 'Premier League': [matches...], ...}
        """
        all_odds = {}
        
        try:
            for league, url in self.LEAGUES.items():
                print(f"   → Scraping {league}...", end=" ")
                matches = self.scrape_league_odds(league)
                all_odds[league] = matches
                print(f"OK ({len(matches)} partite)")
                time.sleep(1)  # Rate limiting
        finally:
            self._cleanup()
        
        return all_odds
    
    def get_match_odds(self, home: str, away: str, league: str, all_odds: dict = None) -> dict:
        """
        Trova le quote per una partita specifica.
        Usa fuzzy matching per gestire differenze nei nomi.
        """
        if all_odds is None:
            all_odds = self.scrape_all_leagues()
        
        league_odds = all_odds.get(league, [])
        
        # Normalizza nomi per matching
        home_lower = home.lower()
        away_lower = away.lower()
        
        for match in league_odds:
            m_home = match.get('home', '').lower()
            m_away = match.get('away', '').lower()
            
            # Match esatto o parziale
            if (home_lower in m_home or m_home in home_lower) and \
               (away_lower in m_away or m_away in away_lower):
                return {
                    '1': match.get('odds_1'),
                    'X': match.get('odds_x'),
                    '2': match.get('odds_2'),
                }
        
        return None


if __name__ == "__main__":
    # Test
    scraper = OddsportalScraper()
    print("Scraping odds from Oddsportal...")
    all_odds = scraper.scrape_all_leagues()
    
    print("\nRisultati:")
    for league, matches in all_odds.items():
        print(f"\n{league}:")
        for m in matches[:3]:
            print(f"  {m['home']} vs {m['away']}: {m['odds_1']} / {m['odds_x']} / {m['odds_2']}")
