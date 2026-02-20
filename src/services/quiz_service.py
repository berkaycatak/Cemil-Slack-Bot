"""
Quiz iş mantığı servisi.
AI ile soru üretme, cevap kontrolü, skor hesaplama ve liderlik tablosu.
"""

import json
from typing import Optional
from src.core.logger import logger
from src.core.exceptions import QuizError


# AI quiz soru üretim prompt'u
QUIZ_GENERATION_PROMPT = """Sen bir teknik bilgi yarışması soru üreticisisin.
Aşağıdaki teknik terimlerden 3 çoktan seçmeli soru üret.
Her sorunun 4 seçeneği (A, B, C, D) olsun. Sadece 1 doğru cevap.
Sorular Türkçe olsun.

SADECE JSON yanıt ver, başka hiçbir şey yazma:
{"questions": [{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"A","explanation":"..."}]}"""

POINTS_PER_CORRECT = 10


class QuizService:
    """
    Quiz sistemi iş mantığı.
    Handler → QuizService → Repositories + GroqClient
    """

    MIN_TERMS_FOR_QUIZ = 5

    def __init__(self, groq_client, term_repo, session_repo, answer_repo):
        self.groq = groq_client
        self.term_repo = term_repo
        self.session_repo = session_repo
        self.answer_repo = answer_repo

    # ── Quiz Başlatma ────────────────────────────────────────────

    async def start_quiz(self, user_id: str, category: str) -> Optional[dict]:
        """
        Yeni bir quiz oturumu başlatır.
        Returns: {"session_id", "questions": [...]} veya None (yetersiz terim).
        """
        # 1. Kategorideki terimleri al
        terms = self.term_repo.get_by_category(category)
        if len(terms) < self.MIN_TERMS_FOR_QUIZ:
            return None

        # 2. Groq ile soru üret
        term_list = ", ".join([t["term"] for t in terms[:20]])  # max 20 terim gönder
        try:
            ai_response = await self.groq.quick_ask(
                system_prompt=QUIZ_GENERATION_PROMPT,
                user_prompt=f"Terimler: {term_list}"
            )
            quiz_data = json.loads(ai_response)
            questions = quiz_data.get("questions", [])[:3]
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"[X] Quiz soru üretim hatası: {e}")
            raise QuizError(f"Soru üretilemedi: {e}")

        if len(questions) < 3:
            raise QuizError("Yeterli soru üretilemedi")

        # 3. Session oluştur
        session_id = self.session_repo.create({
            "user_id": user_id,
            "category": category,
            "total_questions": 3,
        })

        # 4. Soruları kaydet
        for i, q in enumerate(questions, 1):
            self.answer_repo.create({
                "session_id": session_id,
                "question_number": i,
                "question_text": q["question"],
                "options": json.dumps(q["options"]),
                "correct_answer": q["correct"],
            })

        return {"session_id": session_id, "questions": questions}

    # ── Soru Cevaplama ───────────────────────────────────────────

    def answer_question(self, session_id: str, user_answer: str) -> dict:
        """
        Mevcut cevaplanmamış soruya cevap verir.
        Returns: {"is_correct", "correct_answer", "completed", "next_question"|"summary"}
        """
        # 1. Cevaplanmamış soruyu bul
        question = self.answer_repo.get_unanswered(session_id)
        if not question:
            return {"is_correct": False, "completed": True, "error": "Cevaplanacak soru yok"}

        # 2. Doğru mu?
        is_correct = user_answer.upper() == question["correct_answer"].upper()

        # 3. Cevabı kaydet
        self.answer_repo.update(question["id"], {
            "user_answer": user_answer.upper(),
            "is_correct": is_correct,
        })

        # 4. Session skorlarını güncelle
        if is_correct:
            session = self.session_repo.get(session_id)
            self.session_repo.update(session_id, {
                "correct_count": (session or {}).get("correct_count", 0) + 1,
                "score": ((session or {}).get("score", 0)) + POINTS_PER_CORRECT,
            })
        else:
            session = self.session_repo.get(session_id)
            self.session_repo.update(session_id, {
                "wrong_count": (session or {}).get("wrong_count", 0) + 1,
            })

        # 5. Sonraki soru var mı?
        next_question = self.answer_repo.get_unanswered(session_id)
        completed = next_question is None

        if completed:
            self.session_repo.update(session_id, {"status": "completed"})

        result = {
            "is_correct": is_correct,
            "correct_answer": question["correct_answer"],
            "completed": completed,
        }

        if completed:
            updated_session = self.session_repo.get(session_id)
            result["summary"] = updated_session

        if not completed and next_question:
            result["next_question"] = next_question

        return result

    # ── Liderlik Tablosu ─────────────────────────────────────────

    def get_leaderboard(self, limit: int = 10):
        """En yüksek toplam skora göre liderlik tablosunu döndürür."""
        return self.session_repo.get_leaderboard(limit=limit)

    def get_user_stats(self, user_id: str):
        """Kullanıcının quiz istatistiklerini döndürür."""
        return self.session_repo.get_user_stats(user_id)

    def get_categories(self):
        """Mevcut quiz kategorilerini döndürür."""
        return self.term_repo.get_categories()
