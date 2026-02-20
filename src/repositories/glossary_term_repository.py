from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient


class GlossaryTermRepository(BaseRepository):
    """
    Glossary terimleri (glossary_terms) için veritabanı erişim sınıfı.
    Terim CRUD + onay durumu, kategori ve tanımsız terim sorguları.
    """

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_terms")

    def get_by_term(self, term: str):
        """Case-insensitive terim araması."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM glossary_terms WHERE LOWER(term) = LOWER(?)", (term,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_approved_without_definitions(self, limit=5, exclude_ids=None):
        """Onaylanmış ama henüz açıklaması olmayan terimleri getirir (günlük bülten için)."""
        exclude_ids = exclude_ids or []
        placeholders = ",".join(["?"] * len(exclude_ids)) if exclude_ids else ""
        exclude_clause = f"AND t.id NOT IN ({placeholders})" if exclude_ids else ""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT t.* FROM glossary_terms t
                LEFT JOIN glossary_definitions d ON t.id = d.term_id
                WHERE t.status = 'approved' AND d.id IS NULL {exclude_clause}
                ORDER BY RANDOM() LIMIT ?
            """, (*exclude_ids, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_approved_with_definitions(self, limit=3, exclude_ids=None):
        """Onaylanmış ve açıklaması olan terimleri getirir (günlük bülten için)."""
        exclude_ids = exclude_ids or []
        placeholders = ",".join(["?"] * len(exclude_ids)) if exclude_ids else ""
        exclude_clause = f"AND t.id NOT IN ({placeholders})" if exclude_ids else ""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT DISTINCT t.* FROM glossary_terms t
                JOIN glossary_definitions d ON t.id = d.term_id
                WHERE t.status = 'approved' {exclude_clause}
                ORDER BY RANDOM() LIMIT ?
            """, (*exclude_ids, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_categories(self):
        """Onaylanmış terimlerin kategori listesini döndürür."""
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM glossary_terms WHERE status = 'approved' ORDER BY category")
            return [r["category"] for r in cursor.fetchall()]

    def get_by_category(self, category: str):
        """Belirli kategorideki onaylanmış terimleri listeler."""
        return self.list(filters={"status": "approved", "category": category})

    def get_all_approved(self):
        """Tüm onaylanmış terimleri listeler (statik HTML için)."""
        return self.list(filters={"status": "approved"})
