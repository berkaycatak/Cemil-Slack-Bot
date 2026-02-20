from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class TournamentParticipantRepository(BaseRepository):
    """
    DB access for tournament_participants table.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "tournament_participants")

    def list_participants(self, tournament_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM tournament_participants
            WHERE tournament_id = ?
            ORDER BY joined_at ASC
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def is_joined(self, tournament_id: str, user_id: str) -> bool:
        query = """
            SELECT 1 FROM tournament_participants
            WHERE tournament_id = ? AND user_id = ?
            LIMIT 1
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id, user_id))
            return cursor.fetchone() is not None

    def count_participants(self, tournament_id: str) -> int:
        query = "SELECT COUNT(*) as cnt FROM tournament_participants WHERE tournament_id = ?"
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id,))
            row = cursor.fetchone()
            return int(row["cnt"]) if row else 0