import sqlite3
from typing import Optional, Dict, Any
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class TournamentRepository(BaseRepository):
    """
    DB access for tournaments table.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "tournaments")

    def get_open_tournament(self) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM tournaments WHERE status = 'OPEN' ORDER BY created_at DESC LIMIT 1"
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_status(self, tournament_id: str, status: str) -> None:
        query = "UPDATE tournaments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (status, tournament_id))
            conn.commit()