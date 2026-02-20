"""
Glossary (Sözlük) iş mantığı servisi.
Terim önerme, AI validasyon, açıklama ekleme, faydalı tepkisi,
admin onay/red, günlük bülten ve statik HTML üretimi.
"""

import json
import os
from datetime import date
from typing import Optional
from src.core.logger import logger
from src.core.exceptions import GlossaryError


# AI terim validasyon prompt'u
TERM_VALIDATION_PROMPT = """Sen bir teknik terim ve konu validasyon asistanısın.
Kullanıcı bir terim veya konu gönderiyor. Görevlerin:
1. Geçerli bir teknik/akademik terim veya konu mu?
2. Geçerlilik skoru (0-10, 7+ = kesinlikle geçerli)
3. Terim mi, konu mu?
4. Kategori (ML, AI, DevOps, Web, Veri Bilimi, Programlama, Matematik, Genel vb.)
5. İlişkili terimler (varsa, en fazla 5)

SADECE JSON yanıt ver, başka hiçbir şey yazma:
{"is_valid":true,"score":8.5,"term_type":"term","category":"ML","related_terms":["SGD","Adam"],"reason":"Geçerli bir optimizasyon terimi"}"""


class GlossaryService:
    """
    Glossary sistemi iş mantığı.
    Handler → GlossaryService → Repositories + GroqClient
    """

    AUTO_APPROVE_THRESHOLD = 7.0

    def __init__(
        self,
        chat_manager,
        groq_client,
        cron_client,
        term_repo,
        definition_repo,
        reaction_repo,
        daily_log_repo,
        daily_reaction_repo,
        user_repo,
    ):
        self.chat = chat_manager
        self.groq = groq_client
        self.cron = cron_client
        self.term_repo = term_repo
        self.definition_repo = definition_repo
        self.reaction_repo = reaction_repo
        self.daily_log_repo = daily_log_repo
        self.daily_reaction_repo = daily_reaction_repo
        self.user_repo = user_repo
        self.admin_channel = os.environ.get("ADMIN_CHANNEL_ID")

    # ── Terim Gönderme (/terim) ──────────────────────────────────

    async def submit_term(self, term: str, user_id: str) -> dict:
        """
        Yeni terim önerisini işler.
        Returns: {"status": "duplicate|invalid|approved|pending", ...}
        """
        # 1. Aynı terim zaten var mı?
        existing = self.term_repo.get_by_term(term)
        if existing:
            return {"status": "duplicate", "term": existing}

        # 2. AI validasyon
        try:
            ai_response = await self.groq.quick_ask(
                system_prompt=TERM_VALIDATION_PROMPT,
                user_prompt=f"Terim: {term}"
            )
            validation = json.loads(ai_response)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"[X] AI validasyon hatası: {e}")
            # AI başarısız olursa pending olarak kaydet
            validation = {
                "is_valid": True, "score": 5.0, "term_type": "term",
                "category": "Genel", "related_terms": [], "reason": "AI yanıt alınamadı"
            }

        # 3. Geçersiz terim
        if not validation.get("is_valid", False):
            return {
                "status": "invalid",
                "reason": validation.get("reason", "Geçerli bir teknik terim değil")
            }

        # 4. Skora göre onay kararı
        score = float(validation.get("score", 0))
        status = "approved" if score >= self.AUTO_APPROVE_THRESHOLD else "pending"

        # 5. Veritabanına kaydet
        term_id = self.term_repo.create({
            "term": term,
            "category": validation.get("category", "Genel"),
            "term_type": validation.get("term_type", "term"),
            "related_terms": json.dumps(validation.get("related_terms", [])),
            "ai_score": score,
            "status": status,
            "submitted_by": user_id,
            "ai_validation": json.dumps(validation),
        })

        result = {
            "status": status,
            "term_id": term_id,
            "score": score,
            "category": validation.get("category", "Genel"),
            "reason": validation.get("reason", ""),
        }

        # 6. Pending ise admin kanalına bildirim gönder
        if status == "pending" and self.admin_channel:
            self._send_admin_approval_request(term_id, term, score, validation, user_id)

        return result

    # ── Açıklama Ekleme (/acikla) ────────────────────────────────

    async def add_definition(self, term_name: str, definition: str, user_id: str) -> dict:
        """
        Mevcut bir terime açıklama ekler.
        Returns: {"status": "term_not_found|already_contributed|success", ...}
        """
        # 1. Terim var mı?
        term = self.term_repo.get_by_term(term_name)
        if not term:
            return {"status": "term_not_found"}

        # 2. Bu kullanıcı zaten açıklama eklemiş mi?
        if self.definition_repo.user_has_contributed(term["id"], user_id):
            return {"status": "already_contributed"}

        # 3. Açıklamayı kaydet
        def_id = self.definition_repo.create({
            "term_id": term["id"],
            "definition": definition,
            "contributor_id": user_id,
        })

        # 4. Terimi gönderen kişiye DM bildirimi
        if term["submitted_by"] != user_id:
            try:
                self.chat.post_message(
                    channel=term["submitted_by"],
                    text=f"Tebrikler! Gönderdiğin *{term['term']}* terimine yeni bir açıklama eklendi."
                )
            except Exception as e:
                logger.warning(f"[!] DM bildirimi gönderilemedi: {e}")

        return {
            "status": "success",
            "definition_id": def_id,
            "term": term,
        }

    # ── Terim Detayı (/glossary) ─────────────────────────────────

    def get_term_detail(self, term_name: str) -> Optional[dict]:
        """Terim bilgisi + tüm açıklamaları döndürür."""
        term = self.term_repo.get_by_term(term_name)
        if not term:
            return None
        definitions = self.definition_repo.get_by_term_id(term["id"])
        return {"term": term, "definitions": definitions}

    # ── Faydalı Tepkisi ──────────────────────────────────────────

    def toggle_helpful(self, definition_id: str, user_id: str) -> bool:
        """
        Faydalı tepkisini toggle eder.
        Returns: True = eklendi, False = kaldırıldı.
        """
        added = self.reaction_repo.toggle_helpful(definition_id, user_id)
        if added:
            self.definition_repo.increment_helpful(definition_id)
        else:
            self.definition_repo.decrement_helpful(definition_id)
        return added

    # ── Admin Onay/Red ───────────────────────────────────────────

    def handle_admin_action(self, term_id: str, action: str) -> bool:
        """Admin terimi onaylar veya reddeder. action: 'approve' | 'reject'"""
        term = self.term_repo.get(term_id)
        if not term:
            return False

        new_status = "approved" if action == "approve" else "rejected"
        self.term_repo.update(term_id, {"status": new_status})
        return True

    # ── Günlük Bülten (Cron) ─────────────────────────────────────

    def send_daily_post(self, channel_id: str):
        """
        Günlük bülteni oluşturur ve gönderir.
        5 açıklanmamış + 3 açıklanmış terim.
        """
        try:
            # Daha önce gönderilmiş terim ID'lerini al (tekrar önleme)
            posted_undefined = self.daily_log_repo.get_posted_term_ids("undefined")
            posted_defined = self.daily_log_repo.get_posted_term_ids("defined")

            # Terimleri seç
            undefined_terms = self.term_repo.get_approved_without_definitions(
                limit=5, exclude_ids=posted_undefined
            )
            defined_terms = self.term_repo.get_approved_with_definitions(
                limit=3, exclude_ids=posted_defined
            )

            if not undefined_terms and not defined_terms:
                logger.info("[i] Günlük bülten: Gönderilebilecek terim yok, bülten atlandı.")
                return

            # Block Kit mesaj oluştur
            blocks = self._build_daily_post_blocks(undefined_terms, defined_terms)
            today = date.today().isoformat()

            response = self.chat.post_message(
                channel=channel_id,
                text=f"Günün Terimleri - {today}",
                blocks=blocks,
            )
            message_ts = response.get("ts", "")

            # Gönderilenleri logla
            for term in undefined_terms:
                self.daily_log_repo.create({
                    "term_id": term["id"],
                    "post_type": "undefined",
                    "message_ts": message_ts,
                    "channel_id": channel_id,
                    "posted_at": today,
                })
            for term in defined_terms:
                self.daily_log_repo.create({
                    "term_id": term["id"],
                    "post_type": "defined",
                    "message_ts": message_ts,
                    "channel_id": channel_id,
                    "posted_at": today,
                })

            logger.info(f"[+] Günlük bülten gönderildi: {len(undefined_terms)} tanımsız, {len(defined_terms)} tanımlı terim")

        except Exception as e:
            logger.error(f"[X] Günlük bülten hatası: {e}")
            raise GlossaryError(f"Günlük bülten gönderilemedi: {e}")

    def record_daily_reaction(self, daily_log_id: str, user_id: str, reaction_type: str):
        """Biliyordum/bilmiyordum tepkisini kaydeder."""
        self.daily_reaction_repo.set_reaction(daily_log_id, user_id, reaction_type)

    # ── Yardımcı Metodlar ─────────────────────────────────────────

    def get_all_terms(self):
        """Tüm onaylanmış terimleri döndürür (HTML üretici için)."""
        return self.term_repo.get_all_approved()

    def get_categories(self):
        """Mevcut kategorileri döndürür."""
        return self.term_repo.get_categories()

    def _send_admin_approval_request(self, term_id, term, score, validation, user_id):
        """Admin kanalına onay isteği mesajı gönderir."""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Yeni Terim Onay Bekliyor"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Terim:* {term}"},
                        {"type": "mrkdwn", "text": f"*AI Skoru:* {score}/10"},
                        {"type": "mrkdwn", "text": f"*Kategori:* {validation.get('category', '-')}"},
                        {"type": "mrkdwn", "text": f"*Gönderen:* <@{user_id}>"},
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*AI Gerekçe:* {validation.get('reason', '-')}"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Onayla"},
                            "style": "primary",
                            "action_id": "glossary_admin_approve",
                            "value": term_id,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reddet"},
                            "style": "danger",
                            "action_id": "glossary_admin_reject",
                            "value": term_id,
                        },
                    ]
                }
            ]
            self.chat.post_message(
                channel=self.admin_channel,
                text=f"Yeni terim onay bekliyor: {term}",
                blocks=blocks,
            )
        except Exception as e:
            logger.error(f"[X] Admin bildirim hatası: {e}")

    def _build_daily_post_blocks(self, undefined_terms, defined_terms):
        """Günlük bülten için Slack Block Kit blokları oluşturur."""
        today = date.today().isoformat()
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Günün Terimleri - {today}"}
            },
        ]

        # Açıklanmamış terimler
        if undefined_terms:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Açıklama Bekleyen Terimler:*\n`/acikla` komutu ile açıklama ekleyebilirsin!"}
            })
            for term in undefined_terms:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{term['term']}* ({term['category']})"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Bilmiyordum"},
                        "action_id": "daily_term_didnt_know",
                        "value": term["id"],
                    }
                })

            blocks.append({"type": "divider"})

        # Açıklanmış terimler
        if defined_terms:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Bugün Öğren:*"}
            })
            for term in defined_terms:
                definitions = self.definition_repo.get_by_term_id(term["id"])
                top_def = definitions[0]["definition"] if definitions else "-"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{term['term']}* ({term['category']})\n> {top_def}"},
                })
                # Biliyordum / Bilmiyordum butonları
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Biliyordum"},
                            "action_id": "daily_term_knew",
                            "value": term["id"],
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Bilmiyordum"},
                            "action_id": "daily_term_didnt_know",
                            "value": term["id"],
                        },
                    ]
                })

        return blocks
