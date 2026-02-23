"""
FOTMOB SCRAPER - Fetch xG and schedule from FotMob API
======================================================
"""

import requests
import json
from datetime import datetime
import time

class FotMobScraper:
    BASE_URL = "https://www.fotmob.com/api"
    
    # Mapping of common league names to FotMob IDs
    LEAGUE_IDS = {
        'Serie A': 55,
        'Premier League': 47,
        'La Liga': 87,
        'Bundesliga': 54,
        'Ligue 1': 53,
        'Eredivisie': 57,
        'Championship': 48,
        'Primeira Liga': 61,
        'Serie B': 56,
        'Belgian Pro League': 40,
        'MLS': 130,
        'Super Lig': 71,
        'Austrian Bundesliga': 38,
        'Swiss Super League': 69,
        'Scottish Premiership': 64,
        'Danish Superliga': 46,
        'Norwegian Eliteserien': 59,
        'Swedish Allsvenskan': 67,
        'Polish Ekstraklasa': 196,
        'Russian Premier League': 63,
        'Mexican Liga MX': 230,
        'Argentine Primera': 112,
        'Brazilian Serie A': 268,
        'Italian Serie B': 86,
    }

    # Internal mapping for Deep Stats API Season IDs (Latest for 2026)
    SEASON_IDS = {
        46: 27018,   # Denmark 2025/2026
        59: 24542,   # Norway 2025
        67: 24511,   # Sweden 2025
        268: 25077,  # Brazil 2025
        86: 27577,   # Italy Serie B 2025/2026
        38: 27185,   # Austria 2025/2026
        69: 27163,   # Switzerland 2025/2026
        196: 27045,  # Poland 2025/2026
        63: 27157,   # Russia 2025/2026
        230: "27048-Clausura", # Mexico 2025/2026
        112: 24590,  # Argentina 2025
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/"
        })

    def get_team_xg_stats(self, league_name):
        """Fetch team xG stats from the league API table."""
        league_id = self.LEAGUE_IDS.get(league_name)
        if not league_id: return None
        
        url = f"{self.BASE_URL}/leagues?id={league_id}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # The xG data is in table[0]['data']['table']['xg']
            xg_data = []
            tables = data.get('table', [])
            if tables:
                table_entry = tables[0]
                # Try new structure: data -> table -> xg
                data_obj = table_entry.get('data', {})
                if isinstance(data_obj, dict):
                    inner_table = data_obj.get('table', {})
                    if isinstance(inner_table, dict):
                        xg_data = inner_table.get('xg', [])
                
                # Fallback to direct 'xg' in table entry if exists
                if not xg_data and 'xg' in table_entry:
                    xg_data = table_entry['xg']
            
            if not xg_data:
                # print(f"No xG data found in primary table for {league_name}, trying deepstats...")
                return self.get_team_xg_stats_v2(league_name, data)
            
            stats = {}
            for item in xg_data:
                team_name = item.get('name') or item.get('teamName')
                stats[team_name] = {
                    'total_xg': float(item.get('xg', 0)),
                    'total_xga': float(item.get('xgConceded', 0)),
                    'matches': int(item.get('played', 1))
                }
            return stats
        except Exception as e:
            print(f"Error fetching xG stats for {league_name}: {e}")
            return None

    def get_team_xg_stats_v2(self, league_name, league_data):
        """Fetch team xG stats using the deepstats API as a fallback."""
        league_id = self.LEAGUE_IDS.get(league_name)
        
        # 1. Try to get season ID from SEASON_IDS mapping first
        season_id = self.SEASON_IDS.get(league_id)
        
        # 2. If not in mapping, try to extract from league_data
        if not season_id:
            seasons = league_data.get('seasons', [])
            if seasons:
                # Some seasons have 'id', some have it in other fields. 
                # This is why the mapping is more reliable.
                season_id = seasons[0].get('id')
        
        if not season_id: return None
        
        # 3. Fetch xG for teams
        xg_url = f"{self.BASE_URL}/data/leagueseasondeepstats?id={league_id}&season={season_id}&type=teams&stat=expected_goals_team"
        xga_url = f"{self.BASE_URL}/data/leagueseasondeepstats?id={league_id}&season={season_id}&type=teams&stat=expected_goals_conceded_team"
        
        try:
            # Fetch xG
            xg_resp = self.session.get(xg_url)
            xg_resp.raise_for_status()
            xg_data = xg_resp.json()
            
            # Fetch xGA
            xga_resp = self.session.get(xga_url)
            xga_resp.raise_for_status()
            xga_data = xga_resp.json()
            
            # Map by team ID
            stats = {}
            # xG data format: list of objects with teamId, teamName, statValue, matches
            for item in xg_data:
                team_id = item.get('teamId')
                matches = item.get('matches', 1)
                stats[team_id] = {
                    'name': item.get('teamName'),
                    'total_xg': float(item.get('statValue', 0)),
                    'matches': int(matches)
                }
                
            for item in xga_data:
                team_id = item.get('teamId')
                if team_id in stats:
                    stats[team_id]['total_xga'] = float(item.get('statValue', 0))
                else:
                    # Fallback if xGA has teams xG doesn't
                    stats[team_id] = {
                        'name': item.get('teamName'),
                        'total_xg': 0,
                        'total_xga': float(item.get('statValue', 0)),
                        'matches': int(item.get('matches', 1))
                    }
            
            # Convert to team name based dictionary
            final_stats = {}
            for tid, s in stats.items():
                final_stats[s['name']] = {
                    'total_xg': s['total_xg'],
                    'total_xga': s.get('total_xga', 0),
                    'matches': s['matches']
                }
            return final_stats
            
        except Exception as e:
            # print(f"Error in deepstats fallback for {league_name}: {e}")
            return None

    def get_matches_for_day(self, date_str=None):
        """Fetch all matches for the day using the correct /api/data/matches endpoint."""
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
        
        url = f"{self.BASE_URL}/data/matches?date={date_str}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            matches = []
            for league_data in data.get('leagues', []):
                league_id = league_data.get('id')
                
                mapped_name = None
                for name, lid in self.LEAGUE_IDS.items():
                    if lid == league_id:
                        mapped_name = name
                        break
                
                if not mapped_name: continue
                
                for match in league_data.get('matches', []):
                    if match.get('status', {}).get('cancelled'): continue
                    
                    matches.append({
                        'league': mapped_name,
                        'home': match.get('home', {}).get('name'),
                        'away': match.get('away', {}).get('name'),
                        'time': match.get('status', {}).get('startTimeStr'),
                        'id': match.get('id'),
                        'date': date_str
                    })
            return matches
        except Exception as e:
            print(f"Error fetching today's matches: {e}")
            return []

    def get_home_away_goal_splits(self, league_name: str) -> dict | None:
        """
        Fetch home/away goal splits from FotMob league standings.
        
        Uses the home/away tables (which have goals scored/conceded per venue)
        to compute venue ratios. These ratios are applied to aggregate xG 
        to estimate venue-specific xG without extra API calls.
        
        Returns:
            Dict keyed by team shortName: {
                'home_goals': int, 'home_conceded': int, 'home_played': int,
                'away_goals': int, 'away_conceded': int, 'away_played': int,
                'home_goal_ratio': float,  # home_goals / total_goals
                'away_goal_ratio': float,  # away_goals / total_goals
            }
            Plus 'league_home_advantage': float (empirical HA from actual goals)
        """
        league_id = self.LEAGUE_IDS.get(league_name)
        if not league_id:
            return None
        
        url = f"{self.BASE_URL}/leagues?id={league_id}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            tables = data.get('table', [])
            if not tables:
                return None
            
            data_obj = tables[0].get('data', {})
            inner_table = data_obj.get('table', {})
            
            home_table = inner_table.get('home', [])
            away_table = inner_table.get('away', [])
            
            if not home_table or not away_table:
                return None
            
            # Build per-team home stats (keyed by team ID for accuracy)
            team_venue = {}
            total_home_goals = 0
            total_away_goals = 0
            total_home_matches = 0
            
            for entry in home_table:
                tid = entry.get('id')
                name = entry.get('shortName') or entry.get('name')
                scores = entry.get('scoresStr', '0-0').split('-')
                goals_for = int(scores[0].strip()) if len(scores) == 2 else 0
                goals_against = int(scores[1].strip()) if len(scores) == 2 else 0
                played = entry.get('played', 0)
                
                team_venue[tid] = {
                    'name': name,
                    'home_goals': goals_for,
                    'home_conceded': goals_against,
                    'home_played': played,
                }
                total_home_goals += goals_for
                total_home_matches += played
            
            for entry in away_table:
                tid = entry.get('id')
                name = entry.get('shortName') or entry.get('name')
                scores = entry.get('scoresStr', '0-0').split('-')
                goals_for = int(scores[0].strip()) if len(scores) == 2 else 0
                goals_against = int(scores[1].strip()) if len(scores) == 2 else 0
                played = entry.get('played', 0)
                
                if tid in team_venue:
                    team_venue[tid]['away_goals'] = goals_for
                    team_venue[tid]['away_conceded'] = goals_against
                    team_venue[tid]['away_played'] = played
                total_away_goals += goals_for
            
            # Calculate ratios for each team
            result = {}
            for tid, tv in team_venue.items():
                if 'away_goals' not in tv:
                    continue
                
                total_goals = tv['home_goals'] + tv['away_goals']
                total_conceded = tv['home_conceded'] + tv['away_conceded']
                
                # Ratio of goals scored at home vs total (for xG splitting)
                home_goal_ratio = tv['home_goals'] / total_goals if total_goals > 0 else 0.55
                away_goal_ratio = tv['away_goals'] / total_goals if total_goals > 0 else 0.45
                
                home_conceded_ratio = tv['home_conceded'] / total_conceded if total_conceded > 0 else 0.45
                away_conceded_ratio = tv['away_conceded'] / total_conceded if total_conceded > 0 else 0.55
                
                result[tv['name']] = {
                    **tv,
                    'home_goal_ratio': home_goal_ratio,
                    'away_goal_ratio': away_goal_ratio,
                    'home_conceded_ratio': home_conceded_ratio,
                    'away_conceded_ratio': away_conceded_ratio,
                }

            # Empirical league home advantage: avg home goals / avg away goals
            if total_home_matches > 0 and total_away_goals > 0:
                avg_home = total_home_goals / total_home_matches
                avg_away = total_away_goals / total_home_matches  # same # of matches
                league_ha = avg_home / avg_away if avg_away > 0 else 1.15
            else:
                league_ha = 1.15
            
            return {
                'teams': result,
                'league_home_advantage': round(league_ha, 3),
            }
        
        except Exception as e:
            print(f"Error fetching home/away splits for {league_name}: {e}")
            return None

if __name__ == "__main__":
    scraper = FotMobScraper()
    print("Testing FotMob Scraper...")
    
    # Test match fetching
    matches = scraper.get_matches_for_day()
    print(f"Found {len(matches)} matches today across tracked leagues.")
    
    # Test xG fetching for Premier League
    print("\nFetching Premier League xG stats...")
    stats = scraper.get_team_xg_stats('Premier League')
    if stats:
        print(f"Successfully fetched stats for {len(stats)} teams.")
        for team, s in list(stats.items())[:5]:
            print(f"  {team}: {s['total_xg']:.2f} xG, {s['total_xga']:.2f} xGA over {s['matches']} matches")
