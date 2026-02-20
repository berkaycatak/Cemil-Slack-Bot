from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class DailyTermLogRepository(BaseRepository):
    """
    Günlük terim gönderi kayıtları (daily_term_logs) için veritabanı erişim sınıfı.
    Daha önce gönderilmiş terimlerin tekrarlanmaması için kullanılır.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "daily_term_logs")

    def get_posted_term_ids(self, post_type: str):
        """Belirli bir gönderi tipinde daha önce paylaşılmış terim ID'lerini döndürür."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT term_id FROM daily_term_logs WHERE post_type = ?", (post_type,))
            return [r["term_id"] for r in cursor.fetchall()]
