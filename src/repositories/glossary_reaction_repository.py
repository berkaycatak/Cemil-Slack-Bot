import uuid

from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class GlossaryReactionRepository(BaseRepository):
    """
    Glossary açıklama tepkileri (glossary_reactions) için veritabanı erişim sınıfı.
    Toggle mantığı: aynı kullanıcı tekrar basarsa tepki kaldırılır.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_reactions")

    def toggle_helpful(self, definition_id: str, user_id: str) -> bool:
        """
        Faydalı tepkisini toggle eder.
        Returns: True = tepki eklendi, False = tepki kaldırıldı.
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM glossary_reactions WHERE definition_id = ? AND user_id = ? AND reaction_type = 'helpful'",
                (definition_id, user_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("DELETE FROM glossary_reactions WHERE id = ?", (existing["id"],))
                conn.commit()
                return False
            else:
                cursor.execute(
                    "INSERT INTO glossary_reactions (id, definition_id, user_id, reaction_type) VALUES (?, ?, ?, 'helpful')",
                    (str(uuid.uuid4()), definition_id, user_id)
                )
                conn.commit()
                return True
