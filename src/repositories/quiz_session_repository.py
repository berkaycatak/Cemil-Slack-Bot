from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class QuizSessionRepository(BaseRepository):
    """
    Quiz oturumları (quiz_sessions) için veritabanı erişim sınıfı.
    Liderlik tablosu ve kullanıcı istatistikleri sorguları.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "quiz_sessions")

    def get_leaderboard(self, limit=10):
        """En yüksek toplam skora göre liderlik tablosu."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id,
                       SUM(score) as total_score,
                       SUM(correct_count) as total_correct,
                       SUM(wrong_count) as total_wrong,
                       COUNT(id) as quiz_count
                FROM quiz_sessions WHERE status = 'completed'
                GROUP BY user_id
                ORDER BY total_score DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_user_stats(self, user_id: str):
        """Bir kullanıcının toplam quiz istatistiklerini döndürür."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(score) as total_score,
                       SUM(correct_count) as total_correct,
                       SUM(wrong_count) as total_wrong,
                       COUNT(id) as quiz_count
                FROM quiz_sessions WHERE user_id = ? AND status = 'completed'
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
