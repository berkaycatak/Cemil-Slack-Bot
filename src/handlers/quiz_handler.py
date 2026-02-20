"""
Quiz komut ve aksiyon handler'ları.
/quiz komutu, kategori seçimi ve soru cevaplama butonları.
"""

import asyncio
import json
from slack_bolt import App
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.commands import ChatManager
from src.services import QuizService, GlossaryService
from src.repositories import UserRepository


def setup_quiz_handlers(
    app: App,
    quiz_service: QuizService,
    glossary_service: GlossaryService,
    chat_manager: ChatManager,
    user_repo: UserRepository,
):
    """Quiz handler'larını kaydeder."""
    settings = get_settings()
    rate_limiter = get_rate_limiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )

    # ── /quiz ────────────────────────────────────────────────────

    @app.command("/quiz")
    def handle_quiz_command(ack, body):
        """Kategori seçim menüsünü gösterir."""
        ack()
        user_id = body["user_id"]
        channel_id = body["channel_id"]

        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        categories = glossary_service.get_categories()
        if not categories:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text="Henüz yeterli terim yok. Quiz başlatmak için sözlüğe terim eklenmelidir."
            )
            return

        # Kategori butonları oluştur
        buttons = []
        for cat in categories[:10]:  # Max 10 kategori
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": cat},
                "action_id": "quiz_select_category",
                "value": cat,
            })

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Bilgi Yarışması"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Hangi kategoriden quiz çözmek istersin?"}
            },
            {
                "type": "actions",
                "elements": buttons,
            }
        ]

        chat_manager.post_ephemeral(
            channel=channel_id, user=user_id,
            text="Quiz - Kategori Seçimi",
            blocks=blocks,
        )

    # ── Kategori Seçimi ──────────────────────────────────────────

    @app.action("quiz_select_category")
    def handle_category_select(ack, body):
        """Seçilen kategoride quiz başlatır ve ilk soruyu gösterir."""
        ack()
        category = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]

        async def process():
            try:
                result = await quiz_service.start_quiz(user_id, category)
                if result is None:
                    chat_manager.post_ephemeral(
                        channel=channel_id, user=user_id,
                        text=f"*{category}* kategorisinde yeterli terim yok (en az 5 gerekli)."
                    )
                    return

                # İlk soruyu göster
                first_question = result["questions"][0]
                blocks = _build_question_blocks(
                    result["session_id"], 1, 3, first_question
                )
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text=f"Quiz Başladı - {category}",
                    blocks=blocks,
                )
                logger.info(f"[+] QUIZ BAŞLADI | Kullanıcı: {user_id} | Kategori: {category}")
            except Exception as e:
                logger.error(f"[X] Quiz başlatma hatası: {e}", exc_info=True)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Quiz başlatılırken bir hata oluştu. Lütfen tekrar dene."
                )

        asyncio.run(process())

    # ── Soru Cevaplama ───────────────────────────────────────────

    @app.action("quiz_answer")
    def handle_quiz_answer(ack, body):
        """Quiz sorusuna cevap verir."""
        ack()
        # value formatı: session_id:answer (ör. "abc123:B")
        value = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]

        parts = value.split(":", 1)
        if len(parts) != 2:
            return

        session_id, user_answer = parts

        try:
            result = quiz_service.answer_question(session_id, user_answer)

            if result.get("completed"):
                # Sonuç kartı göster
                blocks = _build_result_blocks(result, user_id)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Quiz Tamamlandı!",
                    blocks=blocks,
                )
                logger.info(f"[+] QUIZ TAMAMLANDI | Kullanıcı: {user_id}")
            else:
                # Cevap geri bildirimi + sonraki soru
                feedback = "Doğru!" if result["is_correct"] else f"Yanlış! Doğru cevap: {result['correct_answer']}"

                next_q = result.get("next_question")
                if next_q:
                    blocks = [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{feedback}*"}
                        },
                        {"type": "divider"},
                    ]
                    q_data = {
                        "question": next_q["question_text"],
                        "options": json.loads(next_q["options"]) if isinstance(next_q["options"], str) else next_q["options"],
                    }
                    blocks.extend(_build_question_blocks(
                        session_id, next_q["question_number"], 3, q_data
                    ))
                    chat_manager.post_ephemeral(
                        channel=channel_id, user=user_id,
                        text=feedback,
                        blocks=blocks,
                    )
                else:
                    chat_manager.post_ephemeral(
                        channel=channel_id, user=user_id,
                        text=feedback,
                    )
        except Exception as e:
            logger.error(f"[X] Quiz cevap hatası: {e}", exc_info=True)
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text="Cevap işlenirken bir hata oluştu."
            )

    # ── Yardımcı Fonksiyonlar ────────────────────────────────────

    def _build_question_blocks(session_id, question_num, total, question_data):
        """Quiz sorusu için Block Kit blokları oluşturur."""
        options = question_data.get("options", [])
        buttons = []
        for opt in options:
            # "A) ..." formatından harfi çıkar
            letter = opt[0] if opt else "?"
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": opt},
                "action_id": "quiz_answer",
                "value": f"{session_id}:{letter}",
            })

        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Soru {question_num}/{total}:* {question_data['question']}"}
            },
            {
                "type": "actions",
                "elements": buttons,
            }
        ]

    def _build_result_blocks(result, user_id):
        """Quiz sonuç kartı için Block Kit blokları oluşturur."""
        summary = result.get("summary", {})
        correct = summary.get("correct_count", 0) if summary else 0
        wrong = summary.get("wrong_count", 0) if summary else 0
        score = summary.get("score", 0) if summary else 0

        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Quiz Tamamlandı!"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Doğru:* {correct}"},
                    {"type": "mrkdwn", "text": f"*Yanlış:* {wrong}"},
                    {"type": "mrkdwn", "text": f"*Puan:* {score}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Tekrar denemek için `/quiz` yaz!"}
            }
        ]
