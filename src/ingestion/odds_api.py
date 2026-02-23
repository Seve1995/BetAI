"""
THE ODDS API CLIENT - Free tier odds & scores
==============================================

Fetches real-time odds and match scores from The Odds API (the-odds-api.com).
Free tier: 500 credits/month, no credit card needed.

Usage:
    client = OddsAPIClient()
    odds = client.get_odds('soccer_epl')
    scores = client.get_scores('soccer_epl', days_from=1)
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Team name aliases: FotMob short names → common identifiers that match Odds API names
# Used for fuzzy matching between different data sources
TEAM_ALIASES = {
    # Premier League
    'wolves': ['wolverhampton', 'wolverhampton wanderers'],
    'nottm forest': ['nottingham', 'nottingham forest'],
    'spurs': ['tottenham', 'tottenham hotspur'],
    'tottenham': ['tottenham hotspur', 'spurs'],
    'man utd': ['manchester united', 'man united'],
    'man city': ['manchester city', 'man city'],
    'newcastle': ['newcastle united'],
    'leicester': ['leicester city'],
    'west ham': ['west ham united'],
    'brighton': ['brighton and hove albion', 'brighton hove'],
    'leeds': ['leeds united'],
    'ipswich': ['ipswich town'],
    'bournemouth': ['afc bournemouth'],
    'sheffield utd': ['sheffield united'],
    'luton': ['luton town'],
    # La Liga
    'atlético': ['atletico madrid', 'atletico', 'atlético madrid', 'atl. madrid'],
    'atlético madrid': ['atletico madrid', 'atlético', 'atl. madrid'],
    'athletic': ['athletic bilbao', 'athletic club'],
    'betis': ['real betis'],
    'real sociedad': ['real sociedad'],
    'celta vigo': ['celta de vigo', 'rc celta'],
    'alavés': ['alaves', 'deportivo alaves', 'deportivo alavés'],
    'alaves': ['alavés', 'deportivo alaves', 'deportivo alavés'],
    # Serie A
    'inter': ['internazionale', 'inter milan', 'fc internazionale'],
    'milan': ['ac milan'],
    'napoli': ['ssc napoli'],
    'roma': ['as roma'],
    'lazio': ['ss lazio'],
    'juve': ['juventus'],
    'fiorentina': ['acf fiorentina'],
    'atalanta': ['atalanta bc'],
    # Bundesliga
    "m'gladbach": ['monchengladbach', 'borussia monchengladbach', 'gladbach', "mönchengladbach", "borussia mönchengladbach"],
    'dortmund': ['borussia dortmund'],
    'bayern': ['bayern munich', 'bayern münchen', 'fc bayern'],
    'leverkusen': ['bayer leverkusen', 'bayer 04'],
    'rb leipzig': ['rasenballsport leipzig', 'leipzig'],
    'wolfsburg': ['vfl wolfsburg'],
    'frankfurt': ['eintracht frankfurt'],
    'fc heidenheim': ['1. fc heidenheim', 'heidenheim'],
    'st. pauli': ['fc st. pauli', 'fc st pauli', 'st pauli'],
    'vfb stuttgart': ['stuttgart', 'vfb stuttgart'],
    'werder bremen': ['sv werder bremen', 'bremen'],
    'mainz': ['1. fsv mainz 05', 'mainz 05'],
    'freiburg': ['sc freiburg'],
    'augsburg': ['fc augsburg'],
    'hoffenheim': ['tsg hoffenheim'],
    'union berlin': ['1. fc union berlin'],
    'bochum': ['vfl bochum'],
    'holstein kiel': ['kiel'],
    # Ligue 1
    'psg': ['paris saint-germain', 'paris saint germain', 'paris sg'],
    'marseille': ['olympique marseille', 'olympique de marseille', 'om'],
    'lyon': ['olympique lyonnais', 'olympique lyon', 'ol'],
    'rennes': ['stade rennais'],
    'nice': ['ogc nice'],
    'lens': ['rc lens'],
    'monaco': ['as monaco'],
    'lille': ['losc lille', 'losc'],
    'strasbourg': ['rc strasbourg', 'rc strasbourg alsace'],
    'nantes': ['fc nantes'],
    'le havre': ['le havre ac'],
    'auxerre': ['aj auxerre'],
    'angers': ['angers sco'],
    'lorient': ['fc lorient'],
    'reims': ['stade de reims'],
    'montpellier': ['montpellier hsc'],
    'toulouse': ['toulouse fc'],
    'brest': ['stade brestois', 'stade brestois 29'],
    'st etienne': ['saint-etienne', 'as saint-etienne', 'saint etienne', 'st-etienne'],
    'saint-etienne': ['st etienne', 'as saint-etienne'],
}


def _normalize_team_name(name: str) -> set:
    """
    Generate a set of possible name forms for matching.
    Includes: original, aliases, and individual words (3+ chars).
    """
    lower = name.lower().strip()
    forms = {lower}
    
    # Add aliases
    if lower in TEAM_ALIASES:
        forms.update(TEAM_ALIASES[lower])
    
    # Also check if any alias maps TO this name
    for alias, targets in TEAM_ALIASES.items():
        if lower in [t.lower() for t in targets]:
            forms.add(alias)
    
    # Add individual words (3+ chars) for partial matching
    words = set()
    for form in list(forms):
        words.update(w for w in form.split() if len(w) > 2)
    forms.update(words)
    
    return forms


def _teams_match(name1: str, name2: str) -> bool:
    """Check if two team names refer to the same team."""
    forms1 = _normalize_team_name(name1)
    forms2 = _normalize_team_name(name2)
    
    # Direct match in any form
    if forms1 & forms2:
        return True
    
    # Substring match: any form of name1 contained within any form of name2 or vice-versa
    for f1 in forms1:
        if len(f1) > 3:
            for f2 in forms2:
                if len(f2) > 3 and (f1 in f2 or f2 in f1):
                    return True
    
    return False


class OddsAPIClient:
    """
    Client for The Odds API v4.
    
    Endpoints used:
    - GET /v4/sports                    → list available sports (FREE, no credits)
    - GET /v4/sports/{sport}/odds       → get odds for upcoming matches (1 credit per event-market-region)
    - GET /v4/sports/{sport}/scores     → get scores/results (1 credit per event)
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    # Mapping from our league names to The Odds API sport keys
    SPORT_KEYS = {
        'Serie A': 'soccer_italy_serie_a',
        'Premier League': 'soccer_epl',
        'La Liga': 'soccer_spain_la_liga',
        'Bundesliga': 'soccer_germany_bundesliga',
        'Ligue 1': 'soccer_france_ligue_one',
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self.session = requests.Session()
        self.remaining_credits = None  # Updated from response headers
        
    def _request(self, endpoint: str, params: dict = None) -> dict | list | None:
        """Make a GET request to The Odds API."""
        params = params or {}
        params['apiKey'] = self.api_key
        
        try:
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=15)
            
            # Track remaining credits from response headers
            if 'x-requests-remaining' in response.headers:
                self.remaining_credits = int(response.headers['x-requests-remaining'])
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                print("   ❌ Invalid ODDS_API_KEY. Get a free key at https://the-odds-api.com")
            elif response.status_code == 429:
                print("   ❌ Rate limited. Monthly quota exceeded.")
            else:
                print(f"   ❌ HTTP error: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return None
    
    def get_sports(self) -> list:
        """List available in-season sports. FREE - does not cost credits."""
        data = self._request("/sports")
        return data if data else []
    
    def get_odds(self, league: str, markets: str = "h2h") -> list:
        """
        Get odds for upcoming matches in a league.
        
        Cost: 1 credit per event × number of markets × number of regions
        We use region=eu and market=h2h to minimize credit usage.
        
        Args:
            league: Our league name (e.g., 'Premier League')
            markets: Comma-separated markets (h2h, totals, spreads)
            
        Returns:
            List of match dicts with bookmaker odds
        """
        sport_key = self.SPORT_KEYS.get(league)
        if not sport_key:
            return []
        
        data = self._request(f"/sports/{sport_key}/odds", {
            'regions': 'eu',
            'markets': markets,
            'oddsFormat': 'decimal',
        })
        
        return data if data else []
    
    def get_all_odds(self, markets: str = "h2h,totals") -> dict:
        """
        Get odds for all tracked leagues.
        
        Returns:
            Dict: {'Premier League': [matches...], 'Serie A': [matches...], ...}
        """
        all_odds = {}
        for league in self.SPORT_KEYS:
            odds = self.get_odds(league, markets)
            all_odds[league] = odds
            if odds:
                print(f"   ✅ {league}: {len(odds)} matches with odds")
            else:
                print(f"   ⚠️  {league}: no odds available")
        
        if self.remaining_credits is not None:
            print(f"   📊 Credits remaining: {self.remaining_credits}")
        
        return all_odds
    
    def get_scores(self, league: str, days_from: int = 1) -> list:
        """
        Get scores for recent matches (for result resolution).
        
        Cost: 1 credit per event
        
        Args:
            league: Our league name
            days_from: Number of days back to fetch (1-3)
            
        Returns:
            List of match dicts with scores
        """
        sport_key = self.SPORT_KEYS.get(league)
        if not sport_key:
            return []
        
        data = self._request(f"/sports/{sport_key}/scores", {
            'daysFrom': min(days_from, 3),
        })
        
        return data if data else []

    def get_all_scores(self, days_from: int = 1) -> dict:
        """Get scores for all tracked leagues."""
        all_scores = {}
        for league in self.SPORT_KEYS:
            scores = self.get_scores(league, days_from)
            all_scores[league] = scores
        return all_scores
    
    def find_match_odds(self, home: str, away: str, league: str, all_odds: dict) -> dict | None:
        """
        Find odds for a specific match using alias-aware name matching.
        
        Returns:
            Dict with keys '1', 'X', '2', 'over_25', 'under_25' or None
        """
        league_odds = all_odds.get(league, [])
        
        for event in league_odds:
            event_home = event.get('home_team', '')
            event_away = event.get('away_team', '')
            
            # Use alias-aware matching
            home_match = _teams_match(home, event_home)
            away_match = _teams_match(away, event_away)
            
            if home_match and away_match:
                # Extract best odds across bookmakers
                best_odds = {
                    '1': None, 'X': None, '2': None,
                    'over_25': None, 'under_25': None,
                }
                
                for bookmaker in event.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        mkey = market.get('key')
                        
                        if mkey == 'h2h':
                            for outcome in market.get('outcomes', []):
                                name = outcome.get('name', '').lower()
                                price = outcome.get('price')
                                
                                if name == 'draw':
                                    if best_odds['X'] is None or price > best_odds['X']:
                                        best_odds['X'] = price
                                elif _teams_match(event_home, outcome.get('name', '')):
                                    if best_odds['1'] is None or price > best_odds['1']:
                                        best_odds['1'] = price
                                elif _teams_match(event_away, outcome.get('name', '')):
                                    if best_odds['2'] is None or price > best_odds['2']:
                                        best_odds['2'] = price
                        
                        elif mkey == 'totals':
                            for outcome in market.get('outcomes', []):
                                name = outcome.get('name', '').lower()
                                point = outcome.get('point')
                                price = outcome.get('price')
                                
                                # Only care about 2.5 line
                                if point == 2.5:
                                    if name == 'over':
                                        if best_odds['over_25'] is None or price > best_odds['over_25']:
                                            best_odds['over_25'] = price
                                    elif name == 'under':
                                        if best_odds['under_25'] is None or price > best_odds['under_25']:
                                            best_odds['under_25'] = price
                
                if any(v is not None for v in best_odds.values()):
                    return best_odds
        
        return None
    
    def is_configured(self) -> bool:
        """Check if the API key is set."""
        return bool(self.api_key) and self.api_key != "your_odds_api_key_here"


if __name__ == "__main__":
    client = OddsAPIClient()
    
    if not client.is_configured():
        print("❌ Set ODDS_API_KEY in .env")
        print("   Get a free key at: https://the-odds-api.com")
    else:
        print("🔍 Available soccer sports:")
        sports = client.get_sports()
        for s in sports:
            if 'soccer' in s.get('key', ''):
                print(f"   {s['key']}: {s['title']}")
        
        print("\n📊 Fetching Premier League odds...")
        odds = client.get_odds('Premier League')
        for match in odds[:3]:
            print(f"   {match['home_team']} vs {match['away_team']}")
            for bm in match.get('bookmakers', [])[:1]:
                for mkt in bm.get('markets', []):
                    outcomes = [f"{o['name']}={o['price']}" for o in mkt['outcomes']]
                    print(f"      {bm['title']}: {outcomes}")
