
from src.ingestion.fotmob_scraper import FotMobScraper
import json

s = FotMobScraper()
match_id = 4813600 # Everton vs Leeds from previous step
url = f"{s.BASE_URL}/matchDetails?matchId={match_id}"

try:
    print(f"Fetching details for {match_id}...")
    resp = s.session.get(url)
    data = resp.json()
    
    # keys
    print("Top keys:", data.keys())
    
    # content
    content = data.get('content', {})
    print("Content keys:", content.keys())
    
    # Check for matchFacts -> odds or similar
    # Sometimes it's in 'header' or 'content'
    
    # Search for 'odds' recursively
    def find_key(obj, key):
        if isinstance(obj, dict):
            if key in obj: return obj[key]
            for k, v in obj.items():
                res = find_key(v, key)
                if res: return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_key(item, key)
                if res: return res
        return None
        
    odds = find_key(data, 'odds')
    if odds:
        print("Odds found:", json.dumps(odds, indent=2)[:500]) # First 500 chars
    else:
        print("No 'odds' key found in details")

except Exception as e:
    print(e)
