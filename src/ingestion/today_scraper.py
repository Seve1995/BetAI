"""
Today's Match Scraper - Unified Betting Engine
==============================================

Scrapes today's fixtures from Understat using Selenium (JS rendering required).
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import time

class TodayScraper:
    """
    Scrapes today's matches from Understat using Selenium.
    Understat requires JavaScript execution to access match data.
    """
    
    LEAGUE_URLS = {
        'Serie A': 'https://understat.com/league/Serie_A',
        'Premier League': 'https://understat.com/league/EPL',
        'La Liga': 'https://understat.com/league/La_Liga',
        'Bundesliga': 'https://understat.com/league/Bundesliga',
        'Ligue 1': 'https://understat.com/league/Ligue_1',
    }
    
    def __init__(self):
        self.driver = None
    
    def _get_driver(self):
        """Initialize headless Chrome driver."""
        if self.driver is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')  # Suppress logs
            self.driver = webdriver.Chrome(options=options)
        return self.driver

    def _get_league_matches(self, league_name: str) -> list:
        """
        Fetch all matches for a league from Understat via Selenium.
        """
        url = self.LEAGUE_URLS.get(league_name)
        if not url:
            return []
        
        try:
            driver = self._get_driver()
            driver.get(url)
            time.sleep(2)  # Wait for JS to load
            
            # Extract datesData from window object
            dates_data = driver.execute_script('return window.datesData;')
            return dates_data if dates_data else []
            
        except Exception as e:
            print(f"      Error fetching {league_name}: {e}")
            return []

    def get_todays_matches(self) -> list:
        """
        Get all matches scheduled for today across all leagues.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"Looking for matches on: {today}...")
        
        all_matches = []
        
        try:
            for league_name in self.LEAGUE_URLS.keys():
                print(f"   Checking {league_name}...")
                matches = self._get_league_matches(league_name)
                
                if not matches:
                    print(f"      No data found")
                    continue
                
                # Filter for today's matches
                today_matches = []
                for m in matches:
                    match_date = m.get('datetime', '')[:10]
                    if match_date == today:
                        today_matches.append({
                            'id': m.get('id'),
                            'league': league_name,
                            'home': m.get('h', {}).get('title', 'N/A'),
                            'away': m.get('a', {}).get('title', 'N/A'),
                            'time': m.get('datetime', ''),
                            'is_finished': m.get('isResult', False),
                            'home_goals': m.get('goals', {}).get('h'),
                            'away_goals': m.get('goals', {}).get('a'),
                            'home_xg': float(m.get('xG', {}).get('h', 0) or 0),
                            'away_xg': float(m.get('xG', {}).get('a', 0) or 0),
                        })
                
                if today_matches:
                    print(f"      Found {len(today_matches)} matches!")
                    all_matches.extend(today_matches)
                else:
                    print(f"      No matches today")
        finally:
            self._cleanup()
        
        return all_matches

    def get_upcoming_matches(self, days=3) -> list:
        """
        Get all upcoming matches in the next N days.
        """
        today = datetime.now()
        end_date = today + timedelta(days=days)
        
        today_str = today.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"Looking for matches from {today_str} to {end_str}...")
        
        all_matches = []
        
        try:
            for league_name in self.LEAGUE_URLS.keys():
                print(f"   Checking {league_name}...")
                matches = self._get_league_matches(league_name)
                
                if not matches:
                    continue
                
                for m in matches:
                    match_date = m.get('datetime', '')[:10]
                    if today_str <= match_date <= end_str:
                        all_matches.append({
                            'id': m.get('id'),
                            'league': league_name,
                            'home': m.get('h', {}).get('title', 'N/A'),
                            'away': m.get('a', {}).get('title', 'N/A'),
                            'time': m.get('datetime', ''),
                            'is_finished': m.get('isResult', False),
                        })
        finally:
            self._cleanup()
        
        # Sort by date
        all_matches.sort(key=lambda x: x['time'])
        return all_matches

    def _cleanup(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


# Backwards compatibility alias
TodayMatchFinder = TodayScraper
