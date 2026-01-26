
import json
from datetime import datetime

STATE_FILE = "experiment_state.json"

results = {
    "Paris FC vs Angers": "LOSS", # 0-0, Tip 2
    "Alaves vs Real Betis": "LOSS", # 2-1, Tip 2
    "Arsenal vs Manchester United": "WIN", # 2-3, Tip 2
    "Brentford vs Nottingham Forest": "LOSS", # 0-2, Tip 1
    "Crystal Palace vs Chelsea": "LOSS", # 0-3, Tip 1
    "Real Sociedad vs Celta Vigo": "LOSS", # 3-1, Tip 2
    "Genoa vs Bologna": "WIN", # 3-2, Tip 1
    "Lille vs Strasbourg": "LOSS" # 1-4, Tip 1
}

def resolve_bets():
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    
    pending = state.get("pending_bets", [])
    completed = state.get("completed_bets", [])
    
    new_pending = []
    
    total_profit_change = 0
    wins = 0
    losses = 0
    
    print(f"Resolving {len(pending)} bets...")
    
    for bet in pending:
        match_name = bet['match']
        res = results.get(match_name)
        
        if res:
            if res == "WIN":
                profit = bet['stake'] * (bet['odds'] - 1)
                state['current_state']['bankroll'] += profit + bet['stake']
                state['stats']['wins'] += 1
                state['stats']['total_returns'] += profit + bet['stake']
                state['stats']['total_profit'] += profit
                bet['result'] = 'WIN'
                bet['profit'] = profit
                completed.append(bet)
                total_profit_change += profit
                wins += 1
                print(f"WIN: {match_name} (+€{profit:.2f})")
                
            elif res == "LOSS":
                state['stats']['losses'] += 1
                state['stats']['total_profit'] -= bet['stake']
                bet['result'] = 'LOSS'
                bet['profit'] = -bet['stake']
                completed.append(bet)
                total_profit_change -= bet['stake']
                losses += 1
                print(f"LOSS: {match_name} (-€{bet['stake']:.2f})")
        else:
            new_pending.append(bet)
            print(f"PENDING: {match_name}")
            
    state['pending_bets'] = new_pending
    state['completed_bets'] = completed
    state['stats']['pending'] = len(new_pending)
    state['current_state']['day'] = 2 # Advance to Day 2
    state['current_state']['last_run'] = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\nResults: {wins} Wins, {losses} Losses")
    print(f"Bankroll Change: €{total_profit_change:.2f}")
    print(f"New Bankroll: €{state['current_state']['bankroll']:.2f}")
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    resolve_bets()
