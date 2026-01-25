"""
Merger Module - Unified Betting Engine
======================================

Riconcilia i dati provenienti da diverse fonti.
"""

from thefuzz import fuzz, process
from .db_manager import DatabaseManager, Match, TeamMapping

class TeamMerger:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def find_best_match(self, query_name, choices, threshold=80):
        if query_name in choices: return query_name
        match, score = process.extractOne(query_name, choices, scorer=fuzz.token_sort_ratio)
        return match if score >= threshold else None

    def reconcile_league(self, league_name: str, scraper_team_names: list):
        session = self.db.get_session()
        standard_teams = session.query(Match.home_team).filter_by(league=league_name).distinct().all()
        standard_teams = [t[0] for t in standard_teams]
        
        if not standard_teams:
            session.close()
            return

        for s_name in scraper_team_names:
            exists = session.query(TeamMapping).filter_by(alias=s_name, provider='understat').first()
            if not exists:
                match = self.find_best_match(s_name, standard_teams)
                if match:
                    new_map = TeamMapping(standard_name=match, alias=s_name, provider='understat')
                    session.add(new_map)
        
        session.commit()
        session.close()

    def get_standard_name(self, alias, provider='understat'):
        """Utility per convertire un nome scraper in nome standard."""
        session = self.db.get_session()
        mapping = session.query(TeamMapping).filter_by(alias=alias, provider=provider).first()
        session.close()
        return mapping.standard_name if mapping else alias
