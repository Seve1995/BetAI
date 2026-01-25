"""
Configuration Module - Sports Betting Prediction Engine
========================================================

Gestisce il caricamento delle variabili d'ambiente e le impostazioni globali.
Usa python-dotenv per caricare la API key da .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Trova la root del progetto (dove si trova .env)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Carica variabili d'ambiente
load_dotenv(ENV_PATH)


class Settings:
    """
    Configurazione centralizzata per il sistema di betting.
    
    Attributes:
        API_KEY: Chiave RapidAPI per API-Football
        API_HOST: Host endpoint API-Football
        RATE_LIMIT_CALLS: Numero massimo chiamate per periodo
        RATE_LIMIT_PERIOD: Periodo in secondi per rate limiting
        DB_PATH: Path al database SQLite
        DEFAULT_LEAGUE_ID: ID lega default (Serie A = 135)
    """
    
    # API Configuration
    API_KEY: str = os.getenv("API_FOOTBALL_KEY", "")
    API_PROVIDER: str = os.getenv("API_PROVIDER", "rapidapi").lower()  # 'rapidapi' or 'direct'
    
    # Defaults based on provider
    if API_PROVIDER == "direct":
        DEFAULT_HOST = "v3.football.api-sports.io"
        DEFAULT_URL = "https://v3.football.api-sports.io"
    else:
        DEFAULT_HOST = "api-football-v1.p.rapidapi.com"
        DEFAULT_URL = "https://api-football-v1.p.rapidapi.com/v3"

    API_HOST: str = os.getenv("API_FOOTBALL_HOST", DEFAULT_HOST)
    BASE_URL: str = os.getenv("API_FOOTBALL_URL", DEFAULT_URL)
    
    # Rate Limiting (RapidAPI free tier: ~10 requests/minute)
    RATE_LIMIT_CALLS: int = 10
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Database
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DB_PATH: Path = DATA_DIR / "football.db"
    
    # Default Settings
    DEFAULT_LEAGUE_ID: int = 135  # Serie A
    DEFAULT_SEASON: int = 2024  # Use 2024 for Free Plan compatibility until 2025 is available
    
    # Leghe popolari per riferimento
    POPULAR_LEAGUES = {
        "serie_a": 135,
        "serie_b": 136,
        "premier_league": 39,
        "la_liga": 140,
        "bundesliga": 78,
        "ligue_1": 61,
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Verifica che le configurazioni essenziali siano presenti."""
        if not cls.API_KEY or cls.API_KEY == "your_rapidapi_key_here":
            print("\n❌ ERRORE: API_FOOTBALL_KEY non configurata correttamente in .env")
            print(f"👉 Ottieni una chiave qui: https://rapidapi.com/api-sports/api/api-football")
            print(f"👉 Inseriscila in: {ENV_PATH}")
            return False
        return True
    
    @classmethod
    def get_headers(cls) -> dict:
        """Restituisce gli headers per le chiamate API in base al provider."""
        if cls.API_PROVIDER == "direct":
            return {
                "x-apisports-key": cls.API_KEY,
                "x-rapidapi-host": cls.API_HOST  # Sometimes required by proxy
            }
        else:
            return {
                "x-rapidapi-key": cls.API_KEY,
                "x-rapidapi-host": cls.API_HOST
            }


# Singleton instance
settings = Settings()

# Crea la directory data se non esiste
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
