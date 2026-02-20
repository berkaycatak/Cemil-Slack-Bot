"""
QuizService testleri.
Quiz baslatma, soru cevaplama, skor hesaplama ve liderlik tablosunu test eder.
Groq API mock'lanir.
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.services.quiz_service import QuizService


MOCK_QUESTIONS = {
    "questions": [
        {
            "question": "Docker nedir?",
            "options": ["A) Veritabanı", "B) Konteyner platformu", "C) Programlama dili", "D) İşletim sistemi"],
            "correct": "B",
            "explanation": "Docker bir konteyner platformudur."
        },
        {
            "question": "Kubernetes ne işe yarar?",
            "options": ["A) Orkestrasyon", "B) Derleme", "C) Tasarım", "D) Test"],
            "correct": "A",
            "explanation": "Kubernetes konteyner orkestrasyonu yapar."
        },
        {
            "question": "CI/CD ne demektir?",
            "options": ["A) Code Integration", "B) Continuous Integration/Delivery", "C) Container Interface", "D) Cloud Infrastructure"],
            "correct": "B",
            "explanation": "CI/CD sürekli entegrasyon ve dağıtım demektir."
        }
    ]
}


@pytest.fixture
def service():
    groq_client = MagicMock()
    groq_client.quick_ask = AsyncMock()
    term_repo = MagicMock()
    session_repo = MagicMock()
    answer_repo = MagicMock()

    return QuizService(groq_client, term_repo, session_repo, answer_repo)


class TestStartQuiz:
    @pytest.mark.asyncio
    async def test_not_enough_terms(self, service):
        service.term_repo.get_by_category.return_value = [{"term": "Docker"}]
        result = await service.start_quiz("U123", "DevOps")
        assert result is None

    @pytest.mark.asyncio
    async def test_success(self, service):
        service.term_repo.get_by_category.return_value = [
            {"term": f"Term{i}"} for i in range(10)
        ]
        service.groq.quick_ask.return_value = json.dumps(MOCK_QUESTIONS)
        service.session_repo.create.return_value = "session-1"
        service.answer_repo.create.return_value = "answer-1"

        result = await service.start_quiz("U123", "DevOps")
        assert result is not None
        assert result["session_id"] == "session-1"
        assert len(result["questions"]) == 3


class TestAnswerQuestion:
    def test_correct_answer(self, service):
        service.answer_repo.get_unanswered.return_value = {
            "id": "a1", "session_id": "s1", "question_number": 1,
            "correct_answer": "B", "question_text": "Docker nedir?"
        }
        # Simulate remaining unanswered question
        service.answer_repo.get_unanswered.side_effect = [
            {"id": "a1", "session_id": "s1", "question_number": 1, "correct_answer": "B", "question_text": "Docker nedir?"},
            {"id": "a2", "session_id": "s1", "question_number": 2, "correct_answer": "A", "question_text": "K8s?"},
        ]
        result = service.answer_question("s1", "B")
        assert result["is_correct"] is True
        assert result["completed"] is False

    def test_wrong_answer(self, service):
        service.answer_repo.get_unanswered.side_effect = [
            {"id": "a1", "session_id": "s1", "question_number": 1, "correct_answer": "B", "question_text": "?"},
            {"id": "a2", "session_id": "s1", "question_number": 2, "correct_answer": "A", "question_text": "?"},
        ]
        result = service.answer_question("s1", "C")
        assert result["is_correct"] is False

    def test_last_question_completes_session(self, service):
        service.answer_repo.get_unanswered.side_effect = [
            {"id": "a3", "session_id": "s1", "question_number": 3, "correct_answer": "B", "question_text": "?"},
            None,  # No more unanswered
        ]
        service.session_repo.get.return_value = {
            "id": "s1", "correct_count": 2, "wrong_count": 0, "score": 20
        }
        result = service.answer_question("s1", "B")
        assert result["completed"] is True


class TestGetLeaderboard:
    def test_returns_leaderboard(self, service):
        service.session_repo.get_leaderboard.return_value = [
            {"user_id": "U1", "total_score": 50},
            {"user_id": "U2", "total_score": 30},
        ]
        result = service.get_leaderboard()
        assert len(result) == 2
        assert result[0]["total_score"] > result[1]["total_score"]
