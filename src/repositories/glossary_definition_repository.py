from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class GlossaryDefinitionRepository(BaseRepository):
    """
    Glossary açıklamaları (glossary_definitions) için veritabanı erişim sınıfı.
    Açıklama CRUD + faydalı sayacı ve kullanıcı katkısı sorguları.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_definitions")

    def get_by_term_id(self, term_id: str):
        """Bir terime ait tüm aktif açıklamaları, faydalı sayısına göre sıralı getirir."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM glossary_definitions WHERE term_id = ? AND status = 'active' ORDER BY helpful_count DESC",
                (term_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def user_has_contributed(self, term_id: str, user_id: str) -> bool:
        """Kullanıcı bu terime daha önce açıklama eklemiş mi?"""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM glossary_definitions WHERE term_id = ? AND contributor_id = ?",
                (term_id, user_id)
            )
            return cursor.fetchone() is not None

    def increment_helpful(self, definition_id: str):
        """Denormalize faydalı sayacını 1 artırır."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE glossary_definitions SET helpful_count = helpful_count + 1 WHERE id = ?",
                (definition_id,)
            )
            conn.commit()

    def decrement_helpful(self, definition_id: str):
        """Denormalize faydalı sayacını 1 azaltır (minimum 0)."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE glossary_definitions SET helpful_count = MAX(0, helpful_count - 1) WHERE id = ?",
                (definition_id,)
            )
            conn.commit()
