"""
Glossary repository testleri.
GlossaryTermRepository, GlossaryDefinitionRepository,
GlossaryReactionRepository ve QuizSessionRepository test eder.
"""

import os
import tempfile
import pytest
from src.core.singleton import SingletonMeta
from src.clients.database_client import DatabaseClient
from src.repositories.glossary_term_repository import GlossaryTermRepository
from src.repositories.glossary_definition_repository import GlossaryDefinitionRepository
from src.repositories.glossary_reaction_repository import GlossaryReactionRepository
from src.repositories.quiz_session_repository import QuizSessionRepository


@pytest.fixture
def db():
    # Singleton cache'i temizle — her test temiz DB alsin
    SingletonMeta._instances.pop(DatabaseClient, None)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    client = DatabaseClient(db_path=tmp.name)
    # FK constraint icin test kullanicilari ekle
    with client.get_connection() as conn:
        cursor = conn.cursor()
        for uid in ("U123", "U456", "U789"):
            cursor.execute(
                "INSERT OR IGNORE INTO users (id, slack_id, full_name, cohort) VALUES (?, ?, ?, ?)",
                (uid, uid, f"User {uid}", "test")
            )
        conn.commit()
    yield client
    # Cleanup
    SingletonMeta._instances.pop(DatabaseClient, None)
    os.unlink(tmp.name)


class TestGlossaryTermRepository:
    def test_create_and_get(self, db):
        repo = GlossaryTermRepository(db)
        term_id = repo.create({
            "term": "Docker",
            "category": "DevOps",
            "term_type": "term",
            "ai_score": 8.5,
            "status": "approved",
            "submitted_by": "U123"
        })
        result = repo.get(term_id)
        assert result["term"] == "Docker"
        assert result["category"] == "DevOps"

    def test_get_by_term(self, db):
        repo = GlossaryTermRepository(db)
        repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        result = repo.get_by_term("Docker")
        assert result is not None
        assert result["term"] == "Docker"

    def test_get_by_term_case_insensitive(self, db):
        repo = GlossaryTermRepository(db)
        repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        result = repo.get_by_term("docker")
        assert result is not None

    def test_get_by_term_not_found(self, db):
        repo = GlossaryTermRepository(db)
        result = repo.get_by_term("NonExistent")
        assert result is None

    def test_get_approved_without_definitions(self, db):
        repo = GlossaryTermRepository(db)
        repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        repo.create({"term": "Git", "category": "DevOps", "ai_score": 9.0, "status": "approved", "submitted_by": "U456"})
        results = repo.get_approved_without_definitions(limit=5)
        assert len(results) == 2

    def test_get_categories(self, db):
        repo = GlossaryTermRepository(db)
        repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        repo.create({"term": "Gradient", "category": "ML", "ai_score": 9.0, "status": "approved", "submitted_by": "U123"})
        cats = repo.get_categories()
        assert set(cats) == {"DevOps", "ML"}


class TestGlossaryDefinitionRepository:
    def test_create_and_get_by_term(self, db):
        term_repo = GlossaryTermRepository(db)
        def_repo = GlossaryDefinitionRepository(db)
        term_id = term_repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        def_repo.create({"term_id": term_id, "definition": "Konteyner platformu", "contributor_id": "U456"})
        results = def_repo.get_by_term_id(term_id)
        assert len(results) == 1
        assert results[0]["definition"] == "Konteyner platformu"

    def test_user_already_contributed(self, db):
        term_repo = GlossaryTermRepository(db)
        def_repo = GlossaryDefinitionRepository(db)
        term_id = term_repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        def_repo.create({"term_id": term_id, "definition": "Aciklama 1", "contributor_id": "U456"})
        assert def_repo.user_has_contributed(term_id, "U456") is True
        assert def_repo.user_has_contributed(term_id, "U789") is False

    def test_increment_decrement_helpful(self, db):
        term_repo = GlossaryTermRepository(db)
        def_repo = GlossaryDefinitionRepository(db)
        term_id = term_repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        def_id = def_repo.create({"term_id": term_id, "definition": "Test", "contributor_id": "U456"})

        def_repo.increment_helpful(def_id)
        def_repo.increment_helpful(def_id)
        result = def_repo.get(def_id)
        assert result["helpful_count"] == 2

        def_repo.decrement_helpful(def_id)
        result = def_repo.get(def_id)
        assert result["helpful_count"] == 1


class TestGlossaryReactionRepository:
    def test_toggle_reaction(self, db):
        term_repo = GlossaryTermRepository(db)
        def_repo = GlossaryDefinitionRepository(db)
        react_repo = GlossaryReactionRepository(db)

        term_id = term_repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        def_id = def_repo.create({"term_id": term_id, "definition": "Test", "contributor_id": "U123"})

        # Ilk tepki: ekle
        added = react_repo.toggle_helpful(def_id, "U456")
        assert added is True

        # Ikinci tepki: kaldir
        added = react_repo.toggle_helpful(def_id, "U456")
        assert added is False

    def test_toggle_reacts_again(self, db):
        term_repo = GlossaryTermRepository(db)
        def_repo = GlossaryDefinitionRepository(db)
        react_repo = GlossaryReactionRepository(db)

        term_id = term_repo.create({"term": "Docker", "category": "DevOps", "ai_score": 8.5, "status": "approved", "submitted_by": "U123"})
        def_id = def_repo.create({"term_id": term_id, "definition": "Test", "contributor_id": "U123"})

        react_repo.toggle_helpful(def_id, "U456")  # ekle
        react_repo.toggle_helpful(def_id, "U456")  # kaldir
        added = react_repo.toggle_helpful(def_id, "U456")  # tekrar ekle
        assert added is True


class TestQuizSessionRepository:
    def test_create_and_get_leaderboard(self, db):
        repo = QuizSessionRepository(db)
        repo.create({"user_id": "U123", "category": "ML", "correct_count": 2, "wrong_count": 1, "score": 20, "status": "completed"})
        repo.create({"user_id": "U456", "category": "ML", "correct_count": 3, "wrong_count": 0, "score": 30, "status": "completed"})
        leaderboard = repo.get_leaderboard(limit=10)
        assert len(leaderboard) == 2
        assert leaderboard[0]["total_score"] >= leaderboard[1]["total_score"]

    def test_get_user_stats(self, db):
        repo = QuizSessionRepository(db)
        repo.create({"user_id": "U123", "category": "ML", "correct_count": 2, "wrong_count": 1, "score": 20, "status": "completed"})
        repo.create({"user_id": "U123", "category": "DevOps", "correct_count": 3, "wrong_count": 0, "score": 30, "status": "completed"})
        stats = repo.get_user_stats("U123")
        assert stats["total_score"] == 50
        assert stats["quiz_count"] == 2
