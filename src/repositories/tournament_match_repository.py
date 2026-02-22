from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class TournamentMatchRepository(BaseRepository):
    """
    DB access for tournament_matches table.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "tournament_matches")

    def list_by_round(self, tournament_id: str, round_name: str) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM tournament_matches
            WHERE tournament_id = ? AND round = ?
            ORDER BY match_no ASC
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id, round_name))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def set_winner(self, match_id: str, winner_id: str) -> None:
        query = """
            UPDATE tournament_matches
            SET winner_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (winner_id, match_id))
            conn.commit()

    def list_all(self, tournament_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM tournament_matches
            WHERE tournament_id = ?
            ORDER BY round ASC, match_no ASC
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]