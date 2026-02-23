"""
STATS MANAGER - Team xG statistics & form tracking
===================================================

Manages team-level xG stats, including:
- Season-wide attack/defense ratings (normalized to league average)
- Home/away venue-specific splits (estimated from goal ratios)
- Per-league empirical home advantage
- Bayesian shrinkage for small sample sizes
"""

import json
import os
from datetime import datetime


# Bayesian shrinkage prior strength (in matches)
# Higher = more conservative, more shrinkage toward league average
SHRINKAGE_K = 5


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

    def update_league_stats(self, league_name: str, team_data: dict,
                             venue_data: dict = None):
        """
        Update stats for a league.
        
        Args:
            league_name: e.g. 'Premier League'
            team_data: dict from FotMobScraper.get_team_xg_stats()
                       Format: {team_name: {total_xg, total_xga, matches}}
            venue_data: dict from FotMobScraper.get_home_away_goal_splits()
                       Format: {'teams': {name: {...}}, 'league_home_advantage': float}
        """
        if not team_data:
            return
        
        # Calculate league-wide averages
        total_xg = 0
        total_xga = 0
        total_matches = 0
        
        for team, s in team_data.items():
            total_xg += s['total_xg']
            total_xga += s['total_xga']
            total_matches += s['matches']
            
        avg_xg = total_xg / total_matches if total_matches > 0 else 1.3
        avg_xga = total_xga / total_matches if total_matches > 0 else 1.3
        
        # Merge venue data into team_data
        if venue_data and 'teams' in venue_data:
            venue_teams = venue_data['teams']
            for team_name, td in team_data.items():
                # Try to match by name (FotMob uses shortName in venue data)
                vd = venue_teams.get(team_name)
                if not vd:
                    # Fuzzy match
                    tl = team_name.lower()
                    for vn, vv in venue_teams.items():
                        if tl in vn.lower() or vn.lower() in tl:
                            vd = vv
                            break
                
                if vd:
                    td['home_goal_ratio'] = vd.get('home_goal_ratio', 0.55)
                    td['away_goal_ratio'] = vd.get('away_goal_ratio', 0.45)
                    td['home_conceded_ratio'] = vd.get('home_conceded_ratio', 0.45)
                    td['away_conceded_ratio'] = vd.get('away_conceded_ratio', 0.55)
                    td['home_played'] = vd.get('home_played', 0)
                    td['away_played'] = vd.get('away_played', 0)
        
        # Extract empirical home advantage
        league_ha = 1.15  # Default
        if venue_data:
            league_ha = venue_data.get('league_home_advantage', 1.15)
        
        self.stats[league_name] = {
            'teams': team_data,
            'avg_xg': avg_xg,
            'avg_xga': avg_xga,
            'total_matches': total_matches,
            'home_advantage': league_ha,
            'last_updated': datetime.now().isoformat()
        }
        self.save()

    def save(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def _shrink(self, raw_rating: float, matches: int) -> float:
        """
        Bayesian shrinkage: blend raw rating toward 1.0 (league average).
        
        Formula: (n * raw + k * 1.0) / (n + k)
        
        With k=5, a team with 5 matches gets 50% shrinkage,
        a team with 20 matches gets only 20% shrinkage.
        """
        return (matches * raw_rating + SHRINKAGE_K * 1.0) / (matches + SHRINKAGE_K)

    def get_team_stats(self, league_name: str, team_name: str) -> dict | None:
        """
        Get normalized stats for a specific team.
        
        Returns:
            Dict with:
            - att_rating / def_rating: overall (shrunk)
            - home_att / home_def / away_att / away_def: venue-specific (shrunk)
            - league_avg_xg / league_avg_xga
            - home_advantage: per-league HA factor
            - matches: total matches played
        """
        league = self.stats.get(league_name)
        if not league:
            return None
        
        team = league['teams'].get(team_name)
        if not team:
            # Try fuzzy matching
            team_lower = team_name.lower()
            for stored_name, stored_data in league['teams'].items():
                if (team_lower in stored_name.lower() or 
                    stored_name.lower() in team_lower or
                    any(w in stored_name.lower() for w in team_lower.split() if len(w) > 3)):
                    team = stored_data
                    break
            if not team:
                return None
        
        matches = team['matches']
        team_avg_xg = team['total_xg'] / matches
        team_avg_xga = team['total_xga'] / matches
        
        league_avg_xg = league['avg_xg']
        league_avg_xga = league['avg_xga']
        
        # Raw overall ratings
        raw_att = team_avg_xg / league_avg_xg if league_avg_xg > 0 else 1.0
        raw_def = team_avg_xga / league_avg_xga if league_avg_xga > 0 else 1.0
        
        # Bayesian shrinkage
        att_rating = self._shrink(raw_att, matches)
        def_rating = self._shrink(raw_def, matches)
        
        # Venue-specific ratings (estimated from goal ratios)
        home_ratio = team.get('home_goal_ratio', 0.55)
        away_ratio = team.get('away_goal_ratio', 0.45)
        home_conc_ratio = team.get('home_conceded_ratio', 0.45)
        away_conc_ratio = team.get('away_conceded_ratio', 0.55)
        
        # Home attack: team's home xG (estimated) / league avg
        home_xg_est = team_avg_xg * (home_ratio / 0.5) if home_ratio > 0 else team_avg_xg
        away_xg_est = team_avg_xg * (away_ratio / 0.5) if away_ratio > 0 else team_avg_xg
        
        home_xga_est = team_avg_xga * (home_conc_ratio / 0.5) if home_conc_ratio > 0 else team_avg_xga
        away_xga_est = team_avg_xga * (away_conc_ratio / 0.5) if away_conc_ratio > 0 else team_avg_xga
        
        home_att_raw = home_xg_est / league_avg_xg if league_avg_xg > 0 else 1.0
        home_def_raw = home_xga_est / league_avg_xga if league_avg_xga > 0 else 1.0
        away_att_raw = away_xg_est / league_avg_xg if league_avg_xg > 0 else 1.0
        away_def_raw = away_xga_est / league_avg_xga if league_avg_xga > 0 else 1.0
        
        home_played = team.get('home_played', matches // 2)
        away_played = team.get('away_played', matches // 2)
        
        return {
            'att_rating': att_rating,
            'def_rating': def_rating,
            'home_att': self._shrink(home_att_raw, home_played),
            'home_def': self._shrink(home_def_raw, home_played),
            'away_att': self._shrink(away_att_raw, away_played),
            'away_def': self._shrink(away_def_raw, away_played),
            'avg_xg': team_avg_xg,
            'avg_xga': team_avg_xga,
            'league_avg_xg': league_avg_xg,
            'league_avg_xga': league_avg_xga,
            'home_advantage': league.get('home_advantage', 1.15),
            'matches': matches,
        }
    
    def get_available_leagues(self) -> list:
        """Return list of leagues that have stats loaded."""
        return list(self.stats.keys())
    
    def get_league_teams(self, league_name: str) -> list:
        """Return list of team names in a league."""
        league = self.stats.get(league_name)
        if not league:
            return []
        return list(league['teams'].keys())
