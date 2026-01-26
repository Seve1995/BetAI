
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from ingestion.fotmob_scraper import FotMobScraper
from engine.stats_manager import StatsManager
from engine.prediction_engine import PredictionEngine

def run_analysis():
    print(f"--- DAY 2 ANALYSIS {datetime.now().strftime('%Y-%m-%d')} ---")
    
    scraper = FotMobScraper()
    stats_manager = StatsManager()
    engine = PredictionEngine(stats_manager)
    
    # 1. Update stats (Fast update - in real run we might trust cache or partial update)
    # For now, let's assume stats are reasonably fresh from resolving bets or previous runs.
    # But to be safe, let's update stats for the leagues of today's matches.
    
    print("Fetching today's matches...")
    matches = scraper.get_matches_for_day()
    print(f"Found {len(matches)} matches.")
    
    # Group by league to optimize stats fetching
    leagues_to_update = set(m['league'] for m in matches)
    print(f"updating stats for {len(leagues_to_update)} leagues: {list(leagues_to_update)}")
    
    for league in leagues_to_update:
        try:
            team_stats = scraper.get_team_xg_stats(league)
            if team_stats:
                stats_manager.update_league_stats(league, team_stats)
        except Exception as e:
            print(f"Error updating {league}: {e}")

    # 2. Predict
    potential_bets = []
    
    for match in matches:
        try:
            pred = engine.predict_match(match['league'], match['home'], match['away'])
            if pred:
                # We are looking for Value Bets.
                # Since we don't have odds yet, we can filter by "confident" predictions to save browser time.
                # e.g. Home Win > 50%, Away Win > 40%, or BTTS > 55%
                
                is_interesting = False
                
                # BTTS Strategy
                if pred.get('btts_prob', 0) > 0.55:
                    is_interesting = True
                    
                # 1X2 Strategy (Home Strong)
                if pred.get('home_win_prob', 0) > 0.50:
                    is_interesting = True
                    
                # 1X2 Strategy (Away Strong)
                if pred.get('away_win_prob', 0) > 0.40: # Away wins are harder, lower threshold
                    is_interesting = True
                
                if is_interesting:
                    potential_bets.append({
                        "match": f"{match['home']} vs {match['away']}",
                        "league": match['league'],
                        "home": match['home'],
                        "away": match['away'],
                        "probs": {
                            "1": pred['home_win_prob'],
                            "X": pred['draw_prob'],
                            "2": pred['away_win_prob'],
                            "btts": pred['btts_prob']
                        },
                        "xg": {
                            "home": pred['home_xg_expected'],
                            "away": pred['away_xg_expected']
                        }
                    })
        except Exception as e:
            # print(f"Error predicting {match}: {e}")
            pass
            
    # Output to JSON
    with open("day2_potential_bets.json", "w") as f:
        json.dump(potential_bets, f, indent=2)
        
    print(f"Saved {len(potential_bets)} potential bets to day2_potential_bets.json")

if __name__ == "__main__":
    run_analysis()
