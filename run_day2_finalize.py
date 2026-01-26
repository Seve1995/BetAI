
import json
from datetime import datetime

STATE_FILE = "experiment_state.json"

# Defined manually based on Analysis + Browser Odds
NEW_BETS = [
    {
        "match": "Eyüpspor vs Beşiktaş",
        "date": "2026-01-26",
        "type": "BTTS",
        "prediction": "Yes",
        "odds": 1.85,
        "stake": 4.50, # ~5% of €90.50
        "prob": 0.581,
        "reasoning": "EV: +7.5% (Prob: 58%, Odds: 1.85)"
    }
]

def finalize_day2():
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
        
    current_bankroll = state['current_state']['bankroll']
    pending_bets = state.get('pending_bets', [])
    
    print(f"Current Bankroll: €{current_bankroll:.2f}")
    
    total_stake = 0
    for bet in NEW_BETS:
        if current_bankroll >= bet['stake']:
            current_bankroll -= bet['stake']
            total_stake += bet['stake']
            bet['status'] = 'PENDING'
            pending_bets.append(bet)
            print(f"Placed Bet: {bet['match']} ({bet['type']}) - €{bet['stake']:.2f} @ {bet['odds']}")
        else:
            print(f"Insufficient funds for {bet['match']}")
            
    state['current_state']['bankroll'] = current_bankroll
    state['pending_bets'] = pending_bets
    state['stats']['pending'] = len(pending_bets)
    state['current_state']['last_run'] = datetime.now().strftime("%Y-%m-%d")
    
    # Update stats total_profit (only realized profit goes here usually, but stakes reduce current bankroll)
    # The 'total_profit' metric in the file seems to track realized P/L. 
    # Bankroll tracks available cash.
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
        
    print(f"New Bankroll: €{current_bankroll:.2f}")
    print(f"Total Bets Placed: {len(NEW_BETS)}")

if __name__ == "__main__":
    finalize_day2()
