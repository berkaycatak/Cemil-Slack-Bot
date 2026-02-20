from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class TournamentPointsRepository(BaseRepository):
    """
    tournament_weekly_points tablosu için veritabanı erişim sınıfı.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "tournament_weekly_points")

    def get_points_row(self, week_start: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir hafta ve kullanıcı için puan satırını getirir.
        """
        query = """
            SELECT * FROM tournament_weekly_points
            WHERE week_start = ? AND user_id = ?
            LIMIT 1
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (week_start, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_points(self, week_start: str, user_id: str, delta: int) -> None:
        """
        Upsert benzeri davranış:
        - Eğer kayıt varsa: points += delta
        - Eğer yoksa: yeni satır oluştur ve points = delta yap
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, points FROM tournament_weekly_points WHERE week_start = ? AND user_id = ?",
                (week_start, user_id)
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    """
                    UPDATE tournament_weekly_points
                    SET points = points + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (delta, row["id"])
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO tournament_weekly_points (id, week_start, user_id, points, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (__import__("uuid").uuid4().hex, week_start, user_id, int(delta))
                )

            conn.commit()

    def get_leaderboard(self, week_start: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Belirli haftaya ait en yüksek puanlı kullanıcıları döndürür.
        """
        query = """
            SELECT user_id, points
            FROM tournament_weekly_points
            WHERE week_start = ?
            ORDER BY points DESC
            LIMIT ?
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (week_start, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]