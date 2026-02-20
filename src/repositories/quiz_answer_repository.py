from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class QuizAnswerRepository(BaseRepository):
    """
    Quiz cevapları (quiz_answers) için veritabanı erişim sınıfı.
    Oturumdaki soruları ve cevaplanmamış soruları sorgular.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "quiz_answers")

    def get_by_session(self, session_id: str):
        """Bir oturumdaki tüm soruları sıralı döndürür."""
        return self.list(filters={"session_id": session_id})

    def get_unanswered(self, session_id: str):
        """Oturumdaki henüz cevaplanmamış ilk soruyu döndürür."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM quiz_answers WHERE session_id = ? AND user_answer IS NULL ORDER BY question_number LIMIT 1",
                (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
