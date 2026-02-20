"""
GlossaryService testleri.
AI validasyon, aciklama ekleme, faydali tepkisi ve admin aksiyonlarini test eder.
Dis bagimliliklar (Groq, Slack, DB) mock'lanir.
"""

import json
import pytest
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
    async def test_duplicate_term_returns_duplicate(self, service):
        service.term_repo.get_by_term.return_value = {"id": "existing", "term": "Docker"}
        result = await service.submit_term("Docker", "U123")
        assert result["status"] == "duplicate"

    @pytest.mark.asyncio
    async def test_invalid_term_returns_invalid(self, service):
        service.term_repo.get_by_term.return_value = None
        service.groq.quick_ask.return_value = json.dumps({
            "is_valid": False, "score": 2.0, "term_type": "term",
            "category": "", "related_terms": [], "reason": "Gecersiz terim"
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


class TestToggleHelpful:
    def test_toggle_adds_and_increments(self, service):
        service.reaction_repo.toggle_helpful.return_value = True
        result = service.toggle_helpful("def-1", "U123")
        assert result is True
        service.definition_repo.increment_helpful.assert_called_once_with("def-1")

    def test_toggle_removes_and_decrements(self, service):
        service.reaction_repo.toggle_helpful.return_value = False
        result = service.toggle_helpful("def-1", "U123")
        assert result is False
        service.definition_repo.decrement_helpful.assert_called_once_with("def-1")


class TestAdminAction:
    def test_approve(self, service):
        service.term_repo.get.return_value = {"id": "t1", "term": "Docker", "submitted_by": "U123"}
        result = service.handle_admin_action("t1", "approve")
        assert result is True
        service.term_repo.update.assert_called_once_with("t1", {"status": "approved"})

    def test_reject(self, service):
        service.term_repo.get.return_value = {"id": "t1", "term": "Docker", "submitted_by": "U123"}
        result = service.handle_admin_action("t1", "reject")
        assert result is True
        service.term_repo.update.assert_called_once_with("t1", {"status": "rejected"})

    def test_term_not_found(self, service):
        service.term_repo.get.return_value = None
        result = service.handle_admin_action("nonexistent", "approve")
        assert result is False
