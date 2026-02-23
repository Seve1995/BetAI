"""
DAILY RUNNER - Unified Betting Experiment Pipeline
===================================================

The ONE script to run each day. Replaces all 7+ overlapping entry points.

What it does:
  1. Resolve yesterday's pending bets (automated via FotMob)
  2. Fetch today's matches from FotMob
  3. Update team xG stats from FotMob
  4. Generate predictions using the canonical Poisson model
  5. Fetch live odds from The Odds API
  6. Identify value bets (EV > 5%, Edge > 3%)
  7. Display recommendations and update experiment state

Usage:
    python daily_runner.py             # Full run
    python daily_runner.py --dry-run   # Preview only (no state changes)
    python daily_runner.py --resolve   # Only resolve pending bets
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.fotmob_scraper import FotMobScraper
from src.ingestion.odds_api import OddsAPIClient
from src.engine.stats_manager import StatsManager
from src.engine.prediction_engine import PredictionEngine
from src.engine.match_history import MatchHistory
from src.engine.model_fitter import ModelFitter
from src.engine import calibration


# ─── Constants ────────────────────────────────────────────────────────────────

STATE_FILE = "experiment_state.json"
EXPERIMENT_DOC = "EXPERIMENT.md"

DEFAULT_STRATEGY = {
    "version": "2.1",
    "min_ev": 0.05,          # Only bet if EV > 5%
    "min_edge": 0.03,        # Only bet if our prob > implied + 3%
    "kelly_fraction": 0.25,  # Quarter Kelly for safety
    "max_single_stake_pct": 0.10,  # Max 10% bankroll per bet
    "max_daily_stake_pct": 0.25,   # Max 25% bankroll per day
    "max_odds": 6.0,         # Avoid extreme longshots
}

TRACKED_LEAGUES = [
    'Serie A', 'Premier League', 'La Liga', 'Bundesliga', 'Ligue 1'
]


# ─── State Management ────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load experiment state from JSON file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
    
    return {
        "experiment": {
            "start_date": today,
            "end_date": end_date,
            "initial_bankroll": 100.0
        },
        "current_state": {
            "bankroll": 100.0,
            "day": 1,
            "last_run": None
        },
        "strategy": DEFAULT_STRATEGY,
        "stats": {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_returns": 0.0,
            "total_profit": 0.0
        },
        "pending_bets": [],
        "completed_bets": [],
        "learnings": []
    }


def save_state(state: dict):
    """Save experiment state to JSON file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def reset_experiment(state: dict) -> dict:
    """Reset experiment to fresh start."""
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
    
    return {
        "experiment": {
            "start_date": today,
            "end_date": end_date,
            "initial_bankroll": 100.0
        },
        "current_state": {
            "bankroll": 100.0,
            "day": 1,
            "last_run": None
        },
        "strategy": DEFAULT_STRATEGY,
        "stats": {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_returns": 0.0,
            "total_profit": 0.0
        },
        "pending_bets": [],
        "completed_bets": [],
        "learnings": ["v2.1: Venue-specific ratings, Bayesian shrinkage, O/U 2.5+BTTS markets, per-league HA"]
    }


# ─── Step 1: Resolve Pending Bets ────────────────────────────────────────────

def resolve_pending_bets(state: dict, scraper: FotMobScraper) -> int:
    """
    Automatically resolve pending bets using FotMob match results.
    
    Returns:
        Number of bets resolved
    """
    pending = state.get("pending_bets", [])
    if not pending:
        print("   No pending bets to resolve.")
        return 0
    
    print(f"\n   📋 Resolving {len(pending)} pending bets...")
    
    # Fetch recent results from FotMob
    # Check last 3 days to catch weekend matches
    resolved_count = 0
    still_pending = []
    
    for bet in pending:
        bet_date = bet.get('date', '')
        match_name = bet.get('match', '')
        bet_type = bet.get('type', '1X2')  # Default to 1X2
        tip = bet.get('tip', '')
        
        # Try to find the result via FotMob
        result = _check_match_result(scraper, match_name, bet_date, tip, bet_type)
        
        if result == 'WIN':
            profit = bet['stake'] * (bet['odds'] - 1)
            state['current_state']['bankroll'] += profit + bet['stake']
            state['stats']['wins'] += 1
            state['stats']['total_returns'] += profit + bet['stake']
            state['stats']['total_profit'] += profit
            bet['result'] = 'WIN'
            bet['profit'] = profit
            state['completed_bets'].append(bet)
            resolved_count += 1
            print(f"   ✅ WIN: {match_name} → +€{profit:.2f}")
            
        elif result == 'LOSS':
            state['stats']['losses'] += 1
            state['stats']['total_profit'] -= bet['stake']
            bet['result'] = 'LOSS'
            bet['profit'] = -bet['stake']
            state['completed_bets'].append(bet)
            resolved_count += 1
            print(f"   ❌ LOSS: {match_name} → -€{bet['stake']:.2f}")
            
        else:
            # Still pending or match not found
            still_pending.append(bet)
            print(f"   ⏳ PENDING: {match_name}")
    
    state['pending_bets'] = still_pending
    state['stats']['pending'] = len(still_pending)
    
    return resolved_count


def _check_match_result(scraper: FotMobScraper, match_name: str, 
                         bet_date: str, tip: str, bet_type: str) -> str:
    """
    Check match result via FotMob. 
    Falls back to manual input if automated check fails.
    
    Returns: 'WIN', 'LOSS', or 'PENDING'
    """
    # For now, ask user for results (automated FotMob result checking 
    # would need specific match IDs which we don't always have)
    print(f"\n   Match: {match_name} ({bet_date})")
    print(f"   Tip: {tip} @ {bet_type}")
    
    while True:
        result = input("   Result (W=win, L=loss, P=pending, S=skip): ").strip().upper()
        if result in ('W', 'L', 'P', 'S'):
            break
        print("   Invalid input. Use W, L, P, or S.")
    
    if result == 'W':
        return 'WIN'
    elif result == 'L':
        return 'LOSS'
    else:
        return 'PENDING'


# ─── Step 2-3: Fetch Matches & Update Stats ──────────────────────────────────

def fetch_matches_and_stats(scraper: FotMobScraper, stats_manager: StatsManager) -> list:
    """
    Fetch today's matches and update team xG stats.
    
    Returns:
        List of today's match dicts
    """
    print("\n📊 Updating team xG stats from FotMob...")
    
    for league in TRACKED_LEAGUES:
        try:
            team_stats = scraper.get_team_xg_stats(league)
            venue_data = scraper.get_home_away_goal_splits(league)
            if team_stats:
                stats_manager.update_league_stats(league, team_stats, venue_data)
                ha = venue_data.get('league_home_advantage', '?') if venue_data else '?'
                print(f"   ✅ {league}: {len(team_stats)} teams (HA={ha})")
            else:
                print(f"   ⚠️  {league}: no xG data")
        except Exception as e:
            print(f"   ❌ {league}: {e}")
    
    print("\n🏟️  Fetching today's matches...")
    matches = scraper.get_matches_for_day()
    
    if matches:
        print(f"   Found {len(matches)} matches across tracked leagues")
    else:
        print("   No matches found today")
    
    return matches


# ─── Step 4-6: Predictions & Value Bets ───────────────────────────────────────

def find_value_bets(matches: list, engine: PredictionEngine, 
                     odds_client: OddsAPIClient, strategy: dict, 
                     bankroll: float) -> list:
    """
    Generate predictions and find value bets.
    
    Strategy: Use FotMob matches first, but supplement with Odds API events
    if today's FotMob matches don't have odds (e.g., already kicked off).
    
    Returns:
        List of selected value bet dicts, sorted by EV
    """
    # Fetch all odds
    all_odds = {}
    if odds_client.is_configured():
        print("\n📊 Fetching live odds from The Odds API...")
        all_odds = odds_client.get_all_odds()
    else:
        print("\n⚠️  No ODDS_API_KEY configured. Running predictions only (no EV calculation).")
        print("   Get a free key at: https://the-odds-api.com")
    
    # Generate predictions and find value bets
    all_value_bets = []
    matches_with_odds = 0
    
    # --- Try FotMob matches first ---
    if matches:
        print(f"\n🎯 Analyzing {len(matches)} FotMob matches...")
        
        for match in matches:
            league = match.get('league')
            home = match.get('home')
            away = match.get('away')
            
            if not home or not away:
                continue
            
            # Get prediction
            pred = engine.predict_match(league, home, away)
            if not pred:
                continue
            
            # Try to find odds
            match_odds = None
            if all_odds:
                match_odds = odds_client.find_match_odds(home, away, league, all_odds)
            
            if match_odds:
                matches_with_odds += 1
                vbets = engine.find_value_bets(league, home, away, match_odds, strategy)
                for vb in vbets:
                    vb['match'] = f"{home} vs {away}"
                    vb['league'] = league
                    vb['home'] = home
                    vb['away'] = away
                    vb['time'] = match.get('time', '')
                    vb['stake'] = round(vb['kelly_pct'] * bankroll, 2)
                    all_value_bets.append(vb)
    
    # --- If few FotMob matches had odds, try odds-driven discovery ---
    if all_odds and matches_with_odds < 3:
        print(f"\n🔄 Only {matches_with_odds} FotMob matches had odds. Checking Odds API events...")
        
        for league, events in all_odds.items():
            for event in events:
                home = event.get('home_team', '')
                away = event.get('away_team', '')
                
                if not home or not away:
                    continue
                
                # Skip if already found from FotMob
                already_found = any(
                    vb['home'] == home and vb['away'] == away 
                    for vb in all_value_bets
                )
                if already_found:
                    continue
                
                # Get prediction using the Odds API team names
                pred = engine.predict_match(league, home, away)
                if not pred:
                    continue
                
                # Build odds directly from this event
                match_odds = odds_client.find_match_odds(home, away, league, {league: [event]})
                if not match_odds:
                    continue
                
                matches_with_odds += 1
                vbets = engine.find_value_bets(league, home, away, match_odds, strategy)
                
                commence = event.get('commence_time', '')
                time_str = commence[11:16] if len(commence) > 16 else ''
                
                for vb in vbets:
                    vb['match'] = f"{home} vs {away}"
                    vb['league'] = league
                    vb['home'] = home
                    vb['away'] = away
                    vb['time'] = time_str
                    vb['stake'] = round(vb['kelly_pct'] * bankroll, 2)
                    all_value_bets.append(vb)
    
    if all_odds:
        print(f"   Matches with odds analyzed: {matches_with_odds}")
    
    # Sort by EV and enforce daily stake limit
    all_value_bets.sort(key=lambda x: x['ev'], reverse=True)
    
    max_daily = bankroll * strategy['max_daily_stake_pct']
    selected = []
    total_stake = 0
    
    for bet in all_value_bets:
        if bet['stake'] < 1.00:
            continue
        if total_stake + bet['stake'] <= max_daily:
            selected.append(bet)
            total_stake += bet['stake']
    
    return selected


# ─── Display ──────────────────────────────────────────────────────────────────

def display_predictions(matches: list, engine: PredictionEngine):
    """Show predictions for all matches (even without odds)."""
    print("\n" + "=" * 70)
    print("   📊 TODAY'S PREDICTIONS")
    print("=" * 70)
    
    for match in matches:
        league = match.get('league')
        home = match.get('home')
        away = match.get('away')
        time_str = match.get('time') or ''
        
        if not home or not away:
            continue
        
        pred = engine.predict_match(league, home, away)
        if not pred:
            continue
        
        time_part = f" ({time_str})" if time_str else ""
        source = pred.get('source', 'xg')
        source_tag = "🧠" if source == "fitted" else "📊"
        print(f"\n   {source_tag} [{league}] {home} vs {away}{time_part}")
        print(f"   λ: {pred['home_xg']:.2f} - {pred['away_xg']:.2f}")
        print(f"   1X2: {pred['home_win']:.0%} | {pred['draw']:.0%} | {pred['away_win']:.0%}")
        print(f"   O/U 2.5: {pred['over_25']:.0%} | BTTS: {pred['btts']:.0%}")
        print(f"   Most likely: {pred['most_likely_score']} ({pred['most_likely_score_prob']:.0%})")


def display_value_bets(value_bets: list, bankroll: float):
    """Pretty-print value bet recommendations."""
    if not value_bets:
        print("\n⚠️  No value bets found today.")
        print("   The model didn't find any bets with EV > 5% and Edge > 3%.")
        return
    
    total_stake = sum(b['stake'] for b in value_bets)
    
    print("\n" + "=" * 70)
    print(f"   🔥 {len(value_bets)} VALUE BETS FOUND")
    print("=" * 70)
    
    for i, bet in enumerate(value_bets, 1):
        ev_pct = bet['ev'] * 100
        emoji = "🔥🔥🔥" if ev_pct > 15 else "🔥🔥" if ev_pct > 10 else "🔥" if ev_pct > 5 else "✅"
        
        print(f"\n   {emoji} #{i} {bet['match']}")
        time_str = bet.get('time') or ''
        time_part = f" {time_str}" if time_str else ""
        print(f"      [{bet['league']}]{time_part}")
        print(f"      xG: {bet['home_xg']:.2f} - {bet['away_xg']:.2f}")
        print(f"      TIP: {bet['tip']} @ {bet['odds']:.2f}")
        print(f"      Our Prob: {bet['prob']:.1%} vs Implied: {bet['implied_prob']:.1%}")
        print(f"      EV: +{ev_pct:.1f}% | Edge: +{bet['edge']*100:.1f}%")
        print(f"      Stake: €{bet['stake']:.2f}")
    
    print(f"\n   💰 Total Stake: €{total_stake:.2f} / €{bankroll:.2f} bankroll")
    print("=" * 70)


# ─── Place Bets ───────────────────────────────────────────────────────────────

def place_bets(state: dict, value_bets: list):
    """Record bets in experiment state."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    for bet in value_bets:
        bet_record = {
            'date': today,
            'match': bet['match'],
            'league': bet['league'],
            'tip': bet['tip'],
            'market': bet.get('market', '1X2'),
            'odds': bet['odds'],
            'stake': bet['stake'],
            'ev': bet['ev'],
            'edge': bet['edge'],
            'our_prob': bet['prob'],
            'status': 'PENDING'
        }
        
        state['pending_bets'].append(bet_record)
        state['stats']['total_bets'] += 1
        state['stats']['pending'] += 1
        state['stats']['total_staked'] += bet['stake']
        state['current_state']['bankroll'] -= bet['stake']


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BetAI Daily Experiment Runner")
    parser.add_argument('--dry-run', action='store_true', help="Preview only, no state changes")
    parser.add_argument('--resolve', action='store_true', help="Only resolve pending bets")
    parser.add_argument('--reset', action='store_true', help="Reset experiment to fresh start")
    parser.add_argument('--predictions-only', action='store_true', help="Show predictions without odds")
    parser.add_argument('--seed', action='store_true', help="Seed match history DB from FotMob")
    parser.add_argument('--fit', action='store_true', help="Fit Dixon-Coles parameters via MLE")
    parser.add_argument('--calibrate', action='store_true', help="Show model calibration report")
    args = parser.parse_args()
    
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()
    
    # Initialize components
    scraper = FotMobScraper()
    stats_manager = StatsManager()
    history = MatchHistory()
    odds_client = OddsAPIClient()
    
    # --- Learning engine commands ---
    if args.seed:
        print("\n🌱 Seeding match history database from FotMob...")
        count = history.seed_from_fotmob(scraper, TRACKED_LEAGUES)
        summary = history.summary()
        print(f"\n   ✅ Database seeded: {summary['finished']} finished matches")
        print(f"   Leagues: {', '.join(summary['leagues'])}")
        return
    
    if args.fit:
        fitter = ModelFitter(history)
        fitter.fit_all_leagues(TRACKED_LEAGUES)
        fitter.save()
        return
    
    if args.calibrate:
        report = calibration.generate_report(history)
        print(report)
        return
    
    # Reset if requested
    if args.reset:
        confirm = input("⚠️  Reset experiment? All bets and history will be lost. (y/n): ").strip().lower()
        if confirm == 'y':
            state = reset_experiment(state)
            save_state(state)
            print("✅ Experiment reset! New start date:", today)
        return
    
    # Load fitted parameters if available
    fitter = ModelFitter(history)
    fitted_params = fitter.load()
    engine = PredictionEngine(stats_manager, fitted_params)
    
    if fitted_params:
        n_leagues = len(fitted_params)
        print(f"   🧠 MLE-fitted parameters loaded ({n_leagues} leagues)")
    
    # Header
    print("\n" + "=" * 70)
    print("   🎰 BetAI - Daily Experiment Runner v2.2")
    print("=" * 70)
    print(f"   📅 Date: {today}")
    print(f"   💰 Bankroll: €{state['current_state']['bankroll']:.2f}")
    print(f"   📊 Day: {state['current_state']['day']}/31")
    print(f"   🏆 Record: {state['stats']['wins']}W - {state['stats']['losses']}L")
    
    roi = (state['stats']['total_profit'] / max(state['stats']['total_staked'], 1)) * 100
    print(f"   📈 ROI: {roi:+.1f}%")
    
    # Step 1: Resolve pending bets
    resolved = resolve_pending_bets(state, scraper)
    if resolved > 0:
        print(f"\n   💰 Updated Bankroll: €{state['current_state']['bankroll']:.2f}")
    
    if args.resolve:
        if not args.dry_run:
            save_state(state)
            print("\n✅ State saved.")
        return
    
    # Step 2-3: Fetch matches & update stats
    matches = fetch_matches_and_stats(scraper, stats_manager)
    
    if not matches:
        print("\n⚠️  No matches today. Try again on a match day.")
        if not args.dry_run:
            state['current_state']['last_run'] = today
            save_state(state)
        return
    
    # Step 4: Show predictions
    display_predictions(matches, engine)
    
    if args.predictions_only:
        return
    
    # Step 5-6: Find value bets
    strategy = state.get('strategy', DEFAULT_STRATEGY)
    bankroll = state['current_state']['bankroll']
    value_bets = find_value_bets(matches, engine, odds_client, strategy, bankroll)
    
    # Step 7: Display and confirm
    display_value_bets(value_bets, bankroll)
    
    if args.dry_run:
        print("\n🔍 DRY RUN - no bets placed, no state changes.")
        return
    
    if value_bets:
        confirm = input("\n   Place these bets? (y/n): ").strip().lower()
        
        if confirm == 'y':
            place_bets(state, value_bets)
            print(f"\n   ✅ {len(value_bets)} bets placed!")
            print(f"   💰 New bankroll: €{state['current_state']['bankroll']:.2f}")
        else:
            print("\n   ❌ Bets cancelled.")
    
    # Update state
    state['current_state']['last_run'] = today
    state['current_state']['day'] += 1
    save_state(state)
    
    print(f"\n✅ Day complete! Bankroll: €{state['current_state']['bankroll']:.2f}")


if __name__ == "__main__":
    main()
