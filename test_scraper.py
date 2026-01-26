
from src.ingestion.fotmob_scraper import FotMobScraper
import json
import datetime

s = FotMobScraper()
today = datetime.datetime.now().strftime("%Y%m%d")
url = f"{s.BASE_URL}/data/matches?date={today}"

try:
    resp = s.session.get(url)
    data = resp.json()
    
    # metrics
    leagues = data.get('leagues', [])
    print(f"Found {len(leagues)} leagues")
    
    if leagues:
        matches = leagues[0].get('matches', [])
        if matches:
            print("First match keys:", matches[0].keys())
            print("First match status:", matches[0].get('status'))
            # Check for 'odds'
            if 'odds' in matches[0]:
                print("Odds found:", matches[0]['odds'])
            else:
                print("No top-level 'odds' key")
                
            # Dig deeper
            print(json.dumps(matches[0], indent=2))
        else:
            print("No matches in first league")
    else:
        print("No leagues found")

except Exception as e:
    print(e)
