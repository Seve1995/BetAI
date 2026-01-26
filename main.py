"""
MAIN ORCHESTRATOR - Daily Betting Experiment
============================================
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from ingestion.fotmob_scraper import FotMobScraper
from engine.stats_manager import StatsManager
from engine.prediction_engine import PredictionEngine

def run_experiment():
    print(f"--- BETTING EXPERIMENT {datetime.now().strftime('%Y-%m-%d')} ---")
    
    scraper = FotMobScraper()
    stats_manager = StatsManager()
    engine = PredictionEngine(stats_manager)
    
    # 1. Update stats for all tracked leagues
    print("\nUpdating league stats...")
    for league in scraper.LEAGUE_IDS.keys():
        try:
            team_stats = scraper.get_team_xg_stats(league)
            if team_stats:
                stats_manager.update_league_stats(league, team_stats)
                # print(f"  [OK] {league}")
        except Exception as e:
            print(f"  [ERROR] Updating {league}: {e}")
            
    # 2. Fetch today's matches
    print("\nFetching today's matches...")
    matches = scraper.get_matches_for_day()
    print(f"Found {len(matches)} matches in tracked leagues.")
    
    # 3. Generate predictions
    predictions = []
    for match in matches:
        try:
            pred = engine.predict_match(match['league'], match['home'], match['away'])
            if pred:
                # Store prediction for sorting
                predictions.append({
                    **match,
                    **pred
                })
        except Exception:
            continue
            
    # 4. Filter for high confidence BTTS (>60%)
    print("\n--- HIGH CONFIDENCE BTTS TIPS ---")
    btts_tips = [p for p in predictions if p['btts_prob'] > 0.60]
    # Sort by probability
    btts_tips.sort(key=lambda x: x['btts_prob'], reverse=True)
    
    if not btts_tips:
        print("No high confidence tips found today.")
    else:
        for tip in btts_tips:
            print(f"[{tip['league']}] {tip['home']} vs {tip['away']}")
            print(f"   BTTS Prob: {tip['btts_prob']:.2%}")
            print(f"   Expected xG: {tip['home_xg_expected']:.2f} - {tip['away_xg_expected']:.2f}")
            print("-" * 30)

    # 5. Output summary
    print(f"\nExperiment Summary:")
    print(f"  Matches Scanned: {len(matches)}")
    print(f"  Predictions Generated: {len(predictions)}")
    print(f"  Tips Selected: {len(btts_tips)}")

if __name__ == "__main__":
    run_experiment()
