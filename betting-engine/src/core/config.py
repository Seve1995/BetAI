"""
Unified Configuration Module - Sports Betting Prediction Engine
==============================================================

Gestisce il caricamento delle variabili d'ambiente e le impostazioni globali.
Supporta sia API-Football che Ingestione Zero-Cost.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Trova la root del progetto
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Carica variabili d'ambiente
load_dotenv(ENV_PATH)

class Settings:
    """
    Configurazione centralizzata.
    """
    
    # 1. API Configuration (Legacy/Optional)
    API_KEY = os.getenv("API_FOOTBALL_KEY", "")
    API_PROVIDER = os.getenv("API_PROVIDER", "rapidapi").lower()
    
    # 2. Paths
    DATA_DIR = PROJECT_ROOT / "data"
    DB_PATH = DATA_DIR / "betting.db"
    RAW_CSV_DIR = DATA_DIR / "raw_csv"
    
    # 3. Defaults
    DEFAULT_SEASON = 2024
    
    # 4. League Mapping (Standard names)
    LEAGUES = {
        'Serie A': {'code': 'I1', 'id': 135},
        'Serie B': {'code': 'I2', 'id': 136},
        'Premier League': {'code': 'E0', 'id': 39},
        'La Liga': {'code': 'SP1', 'id': 140},
        'Bundesliga': {'code': 'D1', 'id': 78},
        'Ligue 1': {'code': 'F1', 'id': 61},
    }

    @classmethod
    def validate_api(cls) -> bool:
        return bool(cls.API_KEY and cls.API_KEY != "your_rapidapi_key_here")

# Singleton
settings = Settings()

# Assicura che le directory esistano
settings.RAW_CSV_DIR.mkdir(parents=True, exist_ok=True)
