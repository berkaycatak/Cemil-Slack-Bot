import uuid

from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class DailyTermReactionRepository(BaseRepository):
    """
    Günlük bülten tepkileri (daily_term_reactions) için veritabanı erişim sınıfı.
    Kullanıcı başına tek tepki: biliyordum / bilmiyordum.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "daily_term_reactions")

    def set_reaction(self, daily_log_id: str, user_id: str, reaction_type: str):
        """Tepki ekler veya mevcut tepkiyi günceller (kullanıcı başına tek tepki)."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM daily_term_reactions WHERE daily_log_id = ? AND user_id = ?",
                (daily_log_id, user_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE daily_term_reactions SET reaction_type = ? WHERE id = ?",
                    (reaction_type, existing["id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO daily_term_reactions (id, daily_log_id, user_id, reaction_type) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), daily_log_id, user_id, reaction_type)
                )
            conn.commit()

    def get_counts(self, daily_log_id: str):
        """Bir günlük gönderi için tepki sayılarını döndürür (ör. {'biliyordum': 5, 'bilmiyordum': 3})."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT reaction_type, COUNT(*) as count
                FROM daily_term_reactions WHERE daily_log_id = ?
                GROUP BY reaction_type
            """, (daily_log_id,))
            return {r["reaction_type"]: r["count"] for r in cursor.fetchall()}
