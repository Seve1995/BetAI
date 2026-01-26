"""
STATS MANAGER - Handle persistence of team xG/xGA data
=====================================================
"""

import json
import os
from datetime import datetime

class StatsManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, "team_stats.json")
        self._ensure_dir()
        self.stats = self._load_stats()

    def _ensure_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def update_league_stats(self, league_name, team_data):
        """Update stats for a league. team_data is a dict {team_name: {xg, xga, matches}}"""
        if not team_data: return
        
        # Calculate averages for the league (league-wide offensive and defensive strength)
        total_xg = 0
        total_xga = 0
        total_matches = 0
        
        for team, s in team_data.items():
            total_xg += s['total_xg']
            total_xga += s['total_xga']
            total_matches += s['matches']
            
        avg_xg = total_xg / total_matches if total_matches > 0 else 0
        avg_xga = total_xga / total_matches if total_matches > 0 else 0
        
        self.stats[league_name] = {
            'teams': team_data,
            'avg_xg': avg_xg,
            'avg_xga': avg_xga,
            'last_updated': datetime.now().isoformat()
        }
        self.save()

    def save(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def get_team_stats(self, league_name, team_name):
        """Get stats for a specific team, normalized to offensive/defensive ratings."""
        league = self.stats.get(league_name)
        if not league: return None
        
        team = league['teams'].get(team_name)
        if not team: return None
        
        # Normalized ratings:
        # Attacking Rating = Team xG per 90 / League Avg xG per 90
        # Defensive Rating = Team xGA per 90 / League Avg xGA per 90
        
        team_avg_xg = team['total_xg'] / team['matches']
        team_avg_xga = team['total_xga'] / team['matches']
        
        league_avg_xg = league['avg_xg']
        league_avg_xga = league['avg_xga']
        
        return {
            'att_rating': team_avg_xg / league_avg_xg if league_avg_xg > 0 else 1.0,
            'def_rating': team_avg_xga / league_avg_xga if league_avg_xga > 0 else 1.0,
            'avg_xg': team_avg_xg,
            'avg_xga': team_avg_xga,
            'league_avg_xg': league_avg_xg
        }
