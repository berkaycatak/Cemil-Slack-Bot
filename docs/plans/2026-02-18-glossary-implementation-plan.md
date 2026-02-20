# Glossary Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cemil Bot'a topluluk odakli bir Glossary sistemi ekle: terim gonderme, AI validasyon, aciklama ekleme, quiz, gunluk bulten ve statik web sayfasi.

**Architecture:** Mevcut katmanli mimariye (Handler → Service → Repository) sadik kalinarak 7 yeni DB tablosu, 7 repository, 2 service, 2 handler eklenir. AI validasyon ve quiz uretimi Groq API uzerinden yapilir.

**Tech Stack:** Python 3.10+, Slack Bolt, SQLite, Groq API, Pydantic, APScheduler

**Design Doc:** `docs/plans/2026-02-18-glossary-feature-design.md`

---

## Task 1: Veritabani Tablolari ve Migration

**Files:**
- Modify: `src/clients/database_client.py` (`init_db()` metodu icine)
- Create: `migrations/004_add_glossary_tables.sql`

**Step 1: Migration dosyasini olustur**

`migrations/004_add_glossary_tables.sql` dosyasi olustur, 7 tablonun tum CREATE TABLE + CREATE INDEX ifadelerini icerir. Tum SQL, design doc bolum 3'ten alinir.

**Step 2: `database_client.py` icindeki `init_db()` metoduna 7 tabloyu ekle**

`init_db()` metodunun sonuna, mevcut CREATE TABLE ifadelerinin altina ekle. Mevcut tablolarin sirasina uy (once glossary, sonra quiz).

**Step 3: Test et**

```bash
cd /Users/fatiherencetin/Desktop/Cemil_Bot
python -c "
from src.clients.database_client import DatabaseClient
db = DatabaseClient(db_path=':memory:')
db.init_db()
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'glossary_%'\")
tables = [r[0] for r in cursor.fetchall()]
print('Glossary tablolar:', tables)
assert len(tables) >= 3, f'Eksik tablo! {tables}'

cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'quiz_%'\")
quiz_tables = [r[0] for r in cursor.fetchall()]
print('Quiz tablolar:', quiz_tables)
assert len(quiz_tables) >= 2, f'Eksik tablo! {quiz_tables}'

cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'daily_%'\")
daily_tables = [r[0] for r in cursor.fetchall()]
print('Daily tablolar:', daily_tables)
assert len(daily_tables) >= 2, f'Eksik tablo! {daily_tables}'

print('PASS: Tum 7 tablo basariyla olusturuldu')
"
```

**Step 4: Commit**

```bash
git add src/clients/database_client.py migrations/004_add_glossary_tables.sql
git commit -m "feat(glossary): add 7 database tables for glossary and quiz system"
```

---

## Task 2: Validators (Input Validation Modelleri)

**Files:**
- Modify: `src/core/validators.py`
- Create: `tests/test_glossary_validators.py`

**Step 1: Test dosyasini olustur**

```python
# tests/test_glossary_validators.py
import pytest
from src.core.validators import TermRequest, DefinitionRequest


class TestTermRequest:
    def test_valid_term(self):
        req = TermRequest.parse_from_text("Gradient Descent")
        assert req.term == "Gradient Descent"

    def test_empty_term_raises(self):
        with pytest.raises(ValueError):
            TermRequest.parse_from_text("")

    def test_too_long_term_raises(self):
        with pytest.raises(ValueError):
            TermRequest.parse_from_text("a" * 201)

    def test_whitespace_stripped(self):
        req = TermRequest.parse_from_text("  Docker  ")
        assert req.term == "Docker"


class TestDefinitionRequest:
    def test_valid_definition(self):
        req = DefinitionRequest.parse_from_text("Gradient Descent | Bir optimizasyon algoritmasi")
        assert req.term == "Gradient Descent"
        assert req.definition == "Bir optimizasyon algoritmasi"

    def test_missing_separator_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text("Gradient Descent aciklama yok")

    def test_empty_definition_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text("Gradient Descent | ")

    def test_empty_term_raises(self):
        with pytest.raises(ValueError):
            DefinitionRequest.parse_from_text(" | bir aciklama")
```

**Step 2: Testlerin FAIL ettigini dogrula**

```bash
python -m pytest tests/test_glossary_validators.py -v
```
Beklenen: FAIL - `ImportError: cannot import name 'TermRequest'`

**Step 3: Validator modellerini yaz**

`src/core/validators.py` dosyasinin sonuna ekle:

```python
class TermRequest(BaseModel):
    """Terim gonderme komutu icin input validation."""

    term: str = Field(..., description="Terim adi")

    @field_validator('term')
    @classmethod
    def validate_term(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Terim adi bos olamaz')
        if len(v) > 200:
            raise ValueError('Terim adi en fazla 200 karakter olabilir')
        return v

    @classmethod
    def parse_from_text(cls, text: str) -> 'TermRequest':
        if not text or not text.strip():
            raise ValueError("Terim adi gerekli. Ornek: /terim Gradient Descent")
        return cls(term=text.strip())


class DefinitionRequest(BaseModel):
    """Aciklama ekleme komutu icin input validation."""

    term: str = Field(..., description="Terim adi")
    definition: str = Field(..., description="Aciklama metni")

    @field_validator('term')
    @classmethod
    def validate_term(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Terim adi bos olamaz')
        return v

    @field_validator('definition')
    @classmethod
    def validate_definition(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Aciklama bos olamaz')
        if len(v) > 2000:
            raise ValueError('Aciklama en fazla 2000 karakter olabilir')
        return v

    @classmethod
    def parse_from_text(cls, text: str) -> 'DefinitionRequest':
        if not text or '|' not in text:
            raise ValueError("Format: /acikla <terim> | <aciklama>")
        parts = text.split('|', maxsplit=1)
        term = parts[0].strip()
        definition = parts[1].strip()
        if not term:
            raise ValueError("Terim adi bos olamaz")
        if not definition:
            raise ValueError("Aciklama bos olamaz")
        return cls(term=term, definition=definition)
```

**Step 4: Testlerin PASS ettigini dogrula**

```bash
python -m pytest tests/test_glossary_validators.py -v
```
Beklenen: 8 test PASS

**Step 5: Commit**

```bash
git add src/core/validators.py tests/test_glossary_validators.py
git commit -m "feat(glossary): add TermRequest and DefinitionRequest validators with tests"
```

---

## Task 3: Repositories (7 adet)

**Files:**
- Create: `src/repositories/glossary_term_repository.py`
- Create: `src/repositories/glossary_definition_repository.py`
- Create: `src/repositories/glossary_reaction_repository.py`
- Create: `src/repositories/daily_term_log_repository.py`
- Create: `src/repositories/daily_term_reaction_repository.py`
- Create: `src/repositories/quiz_session_repository.py`
- Create: `src/repositories/quiz_answer_repository.py`
- Modify: `src/repositories/__init__.py`
- Create: `tests/test_glossary_repositories.py`

**Step 1: Test dosyasini olustur**

```python
# tests/test_glossary_repositories.py
import pytest
from src.clients.database_client import DatabaseClient
from src.repositories.glossary_term_repository import GlossaryTermRepository
from src.repositories.glossary_definition_repository import GlossaryDefinitionRepository
from src.repositories.glossary_reaction_repository import GlossaryReactionRepository
from src.repositories.quiz_session_repository import QuizSessionRepository


@pytest.fixture
def db():
    client = DatabaseClient(db_path=":memory:")
    client.init_db()
    return client


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


class TestQuizSessionRepository:
    def test_create_and_get_leaderboard(self, db):
        repo = QuizSessionRepository(db)
        repo.create({"user_id": "U123", "category": "ML", "correct_count": 2, "wrong_count": 1, "score": 20, "status": "completed"})
        repo.create({"user_id": "U456", "category": "ML", "correct_count": 3, "wrong_count": 0, "score": 30, "status": "completed"})
        leaderboard = repo.get_leaderboard(limit=10)
        assert len(leaderboard) == 2
        assert leaderboard[0]["total_score"] >= leaderboard[1]["total_score"]
```

**Step 2: Testlerin FAIL ettigini dogrula**

```bash
python -m pytest tests/test_glossary_repositories.py -v
```
Beklenen: FAIL - `ModuleNotFoundError`

**Step 3: 7 repository dosyasini olustur**

Her repository `BaseRepository`'den miras alir. Ozel sorgular icin ek methodlar eklenir:

**`glossary_term_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class GlossaryTermRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_terms")

    def get_by_term(self, term: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM glossary_terms WHERE LOWER(term) = LOWER(?)", (term,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_approved_without_definitions(self, limit=5, exclude_ids=None):
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
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM glossary_terms WHERE status = 'approved' ORDER BY category")
            return [r["category"] for r in cursor.fetchall()]

    def get_by_category(self, category: str):
        return self.list(filters={"status": "approved", "category": category})

    def get_all_approved(self):
        return self.list(filters={"status": "approved"})
```

**`glossary_definition_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class GlossaryDefinitionRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_definitions")

    def get_by_term_id(self, term_id: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM glossary_definitions WHERE term_id = ? AND status = 'active' ORDER BY helpful_count DESC",
                (term_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def user_has_contributed(self, term_id: str, user_id: str) -> bool:
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM glossary_definitions WHERE term_id = ? AND contributor_id = ?",
                (term_id, user_id)
            )
            return cursor.fetchone() is not None

    def increment_helpful(self, definition_id: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE glossary_definitions SET helpful_count = helpful_count + 1 WHERE id = ?", (definition_id,))
            conn.commit()

    def decrement_helpful(self, definition_id: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE glossary_definitions SET helpful_count = MAX(0, helpful_count - 1) WHERE id = ?", (definition_id,))
            conn.commit()
```

**`glossary_reaction_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class GlossaryReactionRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_reactions")

    def toggle_helpful(self, definition_id: str, user_id: str) -> bool:
        """Faydali tepkisini toggle et. True=eklendi, False=kaldirildi."""
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
                import uuid
                cursor.execute(
                    "INSERT INTO glossary_reactions (id, definition_id, user_id, reaction_type) VALUES (?, ?, ?, 'helpful')",
                    (str(uuid.uuid4()), definition_id, user_id)
                )
                conn.commit()
                return True
```

**`daily_term_log_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class DailyTermLogRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "daily_term_logs")

    def get_posted_term_ids(self, post_type: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT term_id FROM daily_term_logs WHERE post_type = ?", (post_type,))
            return [r["term_id"] for r in cursor.fetchall()]
```

**`daily_term_reaction_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class DailyTermReactionRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "daily_term_reactions")

    def set_reaction(self, daily_log_id: str, user_id: str, reaction_type: str):
        """Tepki ekle veya degistir."""
        import uuid
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM daily_term_reactions WHERE daily_log_id = ? AND user_id = ?", (daily_log_id, user_id))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE daily_term_reactions SET reaction_type = ? WHERE id = ?", (reaction_type, existing["id"]))
            else:
                cursor.execute(
                    "INSERT INTO daily_term_reactions (id, daily_log_id, user_id, reaction_type) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), daily_log_id, user_id, reaction_type)
                )
            conn.commit()

    def get_counts(self, daily_log_id: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT reaction_type, COUNT(*) as count
                FROM daily_term_reactions WHERE daily_log_id = ?
                GROUP BY reaction_type
            """, (daily_log_id,))
            return {r["reaction_type"]: r["count"] for r in cursor.fetchall()}
```

**`quiz_session_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class QuizSessionRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "quiz_sessions")

    def get_leaderboard(self, limit=10):
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
```

**`quiz_answer_repository.py`:**
```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class QuizAnswerRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "quiz_answers")

    def get_by_session(self, session_id: str):
        return self.list(filters={"session_id": session_id})

    def get_unanswered(self, session_id: str):
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM quiz_answers WHERE session_id = ? AND user_answer IS NULL ORDER BY question_number LIMIT 1",
                (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
```

**Step 4: `__init__.py` guncelle**

`src/repositories/__init__.py` dosyasina 7 yeni import ve `__all__` ekle.

**Step 5: Testlerin PASS ettigini dogrula**

```bash
python -m pytest tests/test_glossary_repositories.py -v
```
Beklenen: Tum testler PASS

**Step 6: Commit**

```bash
git add src/repositories/ tests/test_glossary_repositories.py
git commit -m "feat(glossary): add 7 repositories with custom queries and tests"
```

---

## Task 4: Exceptions (Opsiyonel)

**Files:**
- Modify: `src/core/exceptions.py`

**Step 1: Iki yeni exception ekle**

```python
class GlossaryError(CemilBotError):
    """Glossary islemleri sirasinda olusan hatalar."""
    pass

class QuizError(CemilBotError):
    """Quiz islemleri sirasinda olusan hatalar."""
    pass
```

**Step 2: Commit**

```bash
git add src/core/exceptions.py
git commit -m "feat(glossary): add GlossaryError and QuizError exceptions"
```

---

## Task 5: GlossaryService

**Files:**
- Create: `src/services/glossary_service.py`
- Create: `tests/test_glossary_service.py`

**Step 1: Test dosyasini olustur**

```python
# tests/test_glossary_service.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock
from src.services.glossary_service import GlossaryService


@pytest.fixture
def service():
    chat_manager = MagicMock()
    groq_client = MagicMock()
    groq_client.quick_ask = AsyncMock()
    cron_client = MagicMock()
    term_repo = MagicMock()
    definition_repo = MagicMock()
    reaction_repo = MagicMock()
    daily_log_repo = MagicMock()
    daily_reaction_repo = MagicMock()
    user_repo = MagicMock()

    return GlossaryService(
        chat_manager, groq_client, cron_client,
        term_repo, definition_repo, reaction_repo,
        daily_log_repo, daily_reaction_repo, user_repo
    )


class TestSubmitTerm:
    @pytest.mark.asyncio
    async def test_duplicate_term_returns_false(self, service):
        service.term_repo.get_by_term.return_value = {"id": "existing", "term": "Docker"}
        result = await service.submit_term("Docker", "U123")
        assert result["status"] == "duplicate"

    @pytest.mark.asyncio
    async def test_invalid_term_returns_false(self, service):
        service.term_repo.get_by_term.return_value = None
        service.groq.quick_ask.return_value = json.dumps({
            "is_valid": False, "score": 2.0, "term_type": "term",
            "category": "", "related_terms": [], "reason": "Gecersiz"
        })
        result = await service.submit_term("asdfghjkl", "U123")
        assert result["status"] == "invalid"

    @pytest.mark.asyncio
    async def test_high_score_auto_approves(self, service):
        service.term_repo.get_by_term.return_value = None
        service.groq.quick_ask.return_value = json.dumps({
            "is_valid": True, "score": 8.5, "term_type": "term",
            "category": "DevOps", "related_terms": ["Kubernetes"],
            "reason": "Gecerli terim"
        })
        service.term_repo.create.return_value = "new-id"
        result = await service.submit_term("Docker", "U123")
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_low_score_goes_pending(self, service):
        service.term_repo.get_by_term.return_value = None
        service.groq.quick_ask.return_value = json.dumps({
            "is_valid": True, "score": 5.0, "term_type": "term",
            "category": "Genel", "related_terms": [],
            "reason": "Belirsiz"
        })
        service.term_repo.create.return_value = "new-id"
        result = await service.submit_term("BlockchainX", "U123")
        assert result["status"] == "pending"


class TestAddDefinition:
    @pytest.mark.asyncio
    async def test_term_not_found(self, service):
        service.term_repo.get_by_term.return_value = None
        result = await service.add_definition("NonExistent", "aciklama", "U123")
        assert result["status"] == "term_not_found"

    @pytest.mark.asyncio
    async def test_already_contributed(self, service):
        service.term_repo.get_by_term.return_value = {"id": "t1", "term": "Docker", "submitted_by": "U999"}
        service.definition_repo.user_has_contributed.return_value = True
        result = await service.add_definition("Docker", "aciklama", "U123")
        assert result["status"] == "already_contributed"

    @pytest.mark.asyncio
    async def test_success(self, service):
        service.term_repo.get_by_term.return_value = {"id": "t1", "term": "Docker", "submitted_by": "U999"}
        service.definition_repo.user_has_contributed.return_value = False
        service.definition_repo.create.return_value = "d1"
        result = await service.add_definition("Docker", "Konteyner platformu", "U123")
        assert result["status"] == "success"
```

**Step 2: Testlerin FAIL ettigini dogrula**

```bash
python -m pytest tests/test_glossary_service.py -v
```

**Step 3: GlossaryService'i implement et**

`src/services/glossary_service.py` dosyasini olustur. Design doc bolum 4'teki akislari takip et:
- `submit_term()`: AI validasyon → skor kontrolu → otomatik onay veya admin'e gonder
- `add_definition()`: Terim kontrolu → tekrar kontrolu → kaydet → bildirim
- `get_term_detail()`: Terim + aciklamalar + helpful sayilari
- `toggle_helpful()`: Reaction toggle + helpful_count guncelle
- `handle_admin_action()`: Onayla/reddet
- `send_daily_post()`: Gunluk bulten olustur ve gonder
- `record_daily_reaction()`: Biliyordum/bilmiyordum kaydet
- `generate_html()`: Statik HTML uret
- `get_all_terms()`: Tum approved terimleri dondur

AI validation icin TERM_VALIDATION_PROMPT design doc'tan alinir.

**Step 4: Testlerin PASS ettigini dogrula**

```bash
python -m pytest tests/test_glossary_service.py -v
```

**Step 5: Commit**

```bash
git add src/services/glossary_service.py tests/test_glossary_service.py
git commit -m "feat(glossary): add GlossaryService with AI validation, definitions, daily post"
```

---

## Task 6: QuizService

**Files:**
- Create: `src/services/quiz_service.py`
- Create: `tests/test_quiz_service.py`

**Step 1: Test dosyasini olustur**

Testler: `start_quiz()`, `answer_question()`, `get_categories()`, `get_leaderboard()` methodlari icin. Groq API mock'lanir.

**Step 2: Testlerin FAIL ettigini dogrula**

**Step 3: QuizService'i implement et**

- `get_categories()`: glossary_term_repo.get_categories()
- `start_quiz()`: Kategori terimlerini cek → Groq ile 3 soru uret → session + answers kaydet
- `answer_question()`: Cevabi kaydet → dogru/yanlis hesapla → score guncelle → son soru ise session'i tamamla
- `get_leaderboard()`: quiz_session_repo.get_leaderboard()

Quiz uretim prompt'u:
```
Asagidaki teknik terimlerden 3 coktan secmeli soru uret.
Her sorunun 4 secenegi (A, B, C, D) olsun. Sadece 1 dogru cevap.
Terimler: [terim listesi]
SADECE JSON yanit ver: {"questions": [{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"A","explanation":"..."}]}
```

**Step 4: Testlerin PASS ettigini dogrula**

**Step 5: `__init__.py` guncelle ve commit**

```bash
git add src/services/ tests/test_quiz_service.py
git commit -m "feat(glossary): add QuizService with AI question generation and scoring"
```

---

## Task 7: Glossary Handler

**Files:**
- Create: `src/handlers/glossary_handler.py`

**Step 1: Handler'i implement et**

`setup_glossary_handlers(app, glossary_service, chat_manager, user_repo)` fonksiyonu icinde:

- `@app.command("/terim")` → `handle_term_command`
- `@app.command("/acikla")` → `handle_definition_command`
- `@app.command("/glossary")` → `handle_glossary_command`
- `@app.action("glossary_admin_approve")` → `handle_admin_approve`
- `@app.action("glossary_admin_reject")` → `handle_admin_reject`
- `@app.action("glossary_helpful")` → `handle_helpful`
- `@app.action("daily_term_knew")` → `handle_daily_knew`
- `@app.action("daily_term_didnt_know")` → `handle_daily_didnt_know`

Her handler mevcut pattern'i takip eder: `ack() → rate_limit → validate → service → log`

**Step 2: `handlers/__init__.py` guncelle**

**Step 3: Commit**

```bash
git add src/handlers/glossary_handler.py src/handlers/__init__.py
git commit -m "feat(glossary): add glossary handler with /terim, /acikla, /glossary commands and action handlers"
```

---

## Task 8: Quiz Handler

**Files:**
- Create: `src/handlers/quiz_handler.py`

**Step 1: Handler'i implement et**

`setup_quiz_handlers(app, quiz_service, glossary_service, chat_manager, user_repo)` fonksiyonu icinde:

- `@app.command("/quiz")` → `handle_quiz_command` (kategori secim butonlari goster)
- `@app.action("quiz_select_category")` → `handle_category_select` (quiz baslat, ilk soruyu goster)
- `@app.action("quiz_answer")` → `handle_quiz_answer` (cevabi isle, sonraki soru veya sonuc)

Quiz sorusu Slack Block Kit formatinda gosterilir (her secenek bir buton).
Sonuc karti: dogru/yanlis sayisi, puan, siralama.

**Step 2: `handlers/__init__.py` guncelle (zaten Task 7'de yapildi, kontrol et)**

**Step 3: Commit**

```bash
git add src/handlers/quiz_handler.py src/handlers/__init__.py
git commit -m "feat(glossary): add quiz handler with /quiz command and interactive question flow"
```

---

## Task 9: bot.py Entegrasyonu

**Files:**
- Modify: `src/bot.py`

**Step 1: 5 bolumde ekleme yap**

Design doc bolum 8'deki bot.py entegrasyon detayini takip et:
1. Import (7 repo + 2 service + 2 handler)
2. Repository ilklendirme (7 satir)
3. Service ilklendirme (2 blok)
4. Handler kaydi (2 satir)
5. Cron job (glossary_daily_post, saat 09:00)

**Step 2: Syntax kontrolu**

```bash
python -c "from src.bot import app; print('bot.py import basarili')"
```

**Step 3: Commit**

```bash
git add src/bot.py
git commit -m "feat(glossary): integrate glossary and quiz into bot.py (repos, services, handlers, cron)"
```

---

## Task 10: Statik HTML Uretici

**Files:**
- Create: `scripts/generate_glossary_html.py`

**Step 1: HTML uretici scripti olustur**

Script, glossary_service.generate_html() metodunu cagirarak veya dogrudan DB'den veri cekip `data/glossary.html` dosyasini olusturur:
- Tum approved terimler, kategorilere gore gruplu
- Her terimin aciklamalari (faydali sayisi ile)
- Client-side arama (JS)
- Kategori filtresi (JS)
- Katki tablosu (en cok aciklama ekleyenler)
- Responsive CSS
- Tek dosya (inline CSS + JS)

**Step 2: Test et**

```bash
python scripts/generate_glossary_html.py
ls -la data/glossary.html
```

**Step 3: Commit**

```bash
git add scripts/generate_glossary_html.py
git commit -m "feat(glossary): add static HTML glossary page generator"
```

---

## Task 11: .env ve Settings Guncelleme

**Files:**
- Modify: `.env.example`
- Modify: `src/core/settings.py`

**Step 1: Yeni environment variable ekle**

`.env.example` icine:
```
# Glossary
GLOSSARY_DAILY_CHANNEL=serbest-kursu
GLOSSARY_MIN_SCORE=7.0
```

`src/core/settings.py` icine:
```python
glossary_daily_channel: Optional[str] = Field(None, description="Gunluk glossary bulteni kanali")
glossary_min_score: float = Field(7.0, description="Otomatik onay icin minimum AI skoru")
```

**Step 2: Commit**

```bash
git add .env.example src/core/settings.py
git commit -m "feat(glossary): add glossary settings (daily channel, min score)"
```

---

## Task 12: Son Kontroller ve Temizlik

**Step 1: Tum testleri calistir**

```bash
python -m pytest tests/ -v
```
Beklenen: Tum testler PASS

**Step 2: Import kontrolu**

```bash
python -c "
from src.bot import app
from src.services import GlossaryService, QuizService
from src.handlers import setup_glossary_handlers, setup_quiz_handlers
print('Tum importlar basarili')
"
```

**Step 3: CHANGELOG.md guncelle**

Yeni versiyon bilgisi ekle.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(glossary): complete glossary feature - final cleanup and changelog"
```

---

## Ozet

| Task | Icerik | Tahmini Dosya |
|------|--------|---------------|
| 1 | DB tablolari + migration | 2 dosya |
| 2 | Validators + testleri | 2 dosya |
| 3 | 7 Repository + testleri | 9 dosya |
| 4 | Exceptions | 1 dosya |
| 5 | GlossaryService + testleri | 2 dosya |
| 6 | QuizService + testleri | 2 dosya |
| 7 | Glossary Handler | 2 dosya |
| 8 | Quiz Handler | 1 dosya |
| 9 | bot.py entegrasyonu | 1 dosya |
| 10 | HTML uretici | 1 dosya |
| 11 | Settings + .env | 2 dosya |
| 12 | Son kontroller | - |
| **Toplam** | **12 task, 12 commit** | **~25 dosya** |
