"""
Unified Main Orchestrator - Sports Betting Engine
=================================================

CLI unica per gestire:
1. Ingestione storica (CSV + xG)
2. Analisi partite di oggi (Scraped)
3. Modelli predittivi

Usage:
    python main.py
"""

import sys
from pathlib import Path

# Fix path per import
sys.path.insert(0, str(Path(__file__).parent))

from src.core.db_manager import DatabaseManager
from src.core.config import settings
from src.core.merger import TeamMerger
from src.ingestion.historics_loader import HistoricsLoader
from src.ingestion.advanced_scraper import AdvancedScraper
from src.ingestion.today_scraper import TodayScraper
from src.models.predictor import MatchPredictor
import time

def display_banner():
    print("""
+==================================================================+
|                                                                  |
|   [*]  UNIFIED PREDICTION ENGINE (ZERO-COST)  [*]                |
|                                                                  |
+==================================================================+
    """)

def run_ingestion(backfill=False):
    db = DatabaseManager()
    db.create_tables()
    loader = HistoricsLoader(db)
    scraper = AdvancedScraper(db)
    
    print("\n📦 Inizio Ingestione Dati...")
    if backfill:
        loader.backfill()
    else:
        loader.backfill(years=[24]) # Solo stagione attuale
        
    print("\n🕷️ Scarico Stats Avanzate (xG)...")
    for l_name in settings.LEAGUES.keys():
        df = scraper.scrape_season(l_name, 2024)
        scraper.save_stats(df, l_name, "2024/2025")
    print("✅ Ingestione completata.")

def analyze_today():
    db = DatabaseManager()
    scraper = TodayScraper()
    merger = TeamMerger(db)
    predictor = MatchPredictor(db)
    
    matches = scraper.get_todays_matches()
    
    if not matches:
        print("\n❌ Nessun match trovato per oggi nelle leghe monitorate.")
        return

    print(f"\n🔮 Analisi Partite di Oggi ({len(matches)} match tip):")
    print("-" * 60)
    
    for m in matches:
        # Converti nomi per il database
        h_std = merger.get_standard_name(m['home'])
        a_std = merger.get_standard_name(m['away'])
        
        # Esegui predizione
        pred = predictor.predict_match(h_std, a_std, m['league'])
        
        print(f"\n📍 {m['league']}: {m['home']} vs {m['away']}")
        
        if pred:
            print(f"   ├─ xG previsti: {pred['home_expect']:.2f} - {pred['away_expect']:.2f}")
            print(f"   ├─ 1X2 Prob: {pred['home_win']:.0%} | {pred['draw']:.0%} | {pred['away_win']:.0%}")
            print(f"   └─ Over 2.5: {pred['over_2.5']:.0%}")
            
            # Tip semplice
            if pred['home_win'] > 0.55: print("   💡 TIP: Casa Vincente")
            elif pred['away_win'] > 0.45: print("   💡 TIP: Trasferta Vincente")
        else:
            print("   ⚠️ Statistiche insufficienti per questo match.")

def main():
    display_banner()
    while True:
        print("\nMENU PRINCIPALE:")
        print("  1. 📁 Aggiorna dati (Solo 2024)")
        print("  2. 📂 Backfill storico (2015-2024 - Richiede tempo!)")
        print("  3. 🔮 ANALIZZA PARTITE DI OGGI")
        print("  0. Esci")
        
        choice = input("\nScelta: ").strip()
        
        if choice == "1": run_ingestion(backfill=False)
        elif choice == "2": run_ingestion(backfill=True)
        elif choice == "3": analyze_today()
        elif choice == "0": break
        else: print("Opzione non valida.")

if __name__ == "__main__":
    main()
