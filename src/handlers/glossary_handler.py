"""
Glossary (Sözlük) komut ve aksiyon handler'ları.
/terim, /acikla, /glossary komutları ve admin onay/red, faydalı, günlük bülten butonları.
"""

import asyncio
import json
from slack_bolt import App
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.core.validators import TermRequest, DefinitionRequest
from src.commands import ChatManager
from src.services import GlossaryService
from src.repositories import UserRepository


def setup_glossary_handlers(
    app: App,
    glossary_service: GlossaryService,
    chat_manager: ChatManager,
    user_repo: UserRepository,
):
    """Glossary handler'larını kaydeder."""
    settings = get_settings()
    rate_limiter = get_rate_limiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )

    # ── /terim <terim_adi> ───────────────────────────────────────

    @app.command("/terim")
    def handle_term_command(ack, body):
        """Yeni terim önerisi gönderir."""
        ack()
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = body.get("text", "").strip()

        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        # Kullanıcı adını al
        try:
            user_data = user_repo.get_by_slack_id(user_id)
            user_name = user_data.get("full_name", user_id) if user_data else user_id
        except Exception:
            user_name = user_id

        logger.info(f"[>] /terim komutu | Kullanıcı: {user_name} ({user_id})")

        # Validation
        try:
            req = TermRequest.parse_from_text(text)
        except ValueError as ve:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text=f"Terim formatı hatalı: {ve}\nKullanım: `/terim Gradient Descent`"
            )
            return

        async def process():
            try:
                result = await glossary_service.submit_term(req.term, user_id)
                status = result["status"]

                if status == "duplicate":
                    msg = f"*{req.term}* terimi zaten sözlükte mevcut."
                elif status == "invalid":
                    msg = f"*{req.term}* geçerli bir teknik terim olarak kabul edilmedi.\nGerekçe: {result.get('reason', '-')}"
                elif status == "approved":
                    msg = (
                        f"*{req.term}* terimi otomatik onaylandı! (AI Skoru: {result['score']}/10)\n"
                        f"Kategori: {result.get('category', '-')}\n"
                        f"Topluluk üyeleri `/acikla {req.term} | açıklama` ile açıklama ekleyebilir."
                    )
                elif status == "pending":
                    msg = (
                        f"*{req.term}* terimi admin onayına gönderildi. (AI Skoru: {result['score']}/10)\n"
                        f"Onaylandığında bilgilendirileceksin."
                    )
                else:
                    msg = "Bir hata oluştu, lütfen tekrar dene."

                chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=msg)
                logger.info(f"[+] TERİM ÖNERİSİ | {user_name} ({user_id}) | Terim: {req.term} | Sonuç: {status}")
            except Exception as e:
                logger.error(f"[X] /terim hatası: {e}", exc_info=True)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Terim gönderilirken bir hata oluştu. Lütfen tekrar dene."
                )

        asyncio.run(process())

    # ── /acikla <terim> | <aciklama> ─────────────────────────────

    @app.command("/acikla")
    def handle_definition_command(ack, body):
        """Mevcut bir terime açıklama ekler."""
        ack()
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = body.get("text", "").strip()

        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        try:
            user_data = user_repo.get_by_slack_id(user_id)
            user_name = user_data.get("full_name", user_id) if user_data else user_id
        except Exception:
            user_name = user_id

        logger.info(f"[>] /acikla komutu | Kullanıcı: {user_name} ({user_id})")

        # Validation
        try:
            req = DefinitionRequest.parse_from_text(text)
        except ValueError as ve:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text=f"Format hatalı: {ve}\nKullanım: `/acikla Docker | Konteyner teknolojisi`"
            )
            return

        async def process():
            try:
                result = await glossary_service.add_definition(req.term, req.definition, user_id)
                status = result["status"]

                if status == "term_not_found":
                    msg = f"*{req.term}* terimi sözlükte bulunamadı. Önce `/terim {req.term}` ile öner."
                elif status == "already_contributed":
                    msg = f"*{req.term}* terimine zaten bir açıklama eklemişsin."
                elif status == "success":
                    msg = f"*{req.term}* terimine açıklaman eklendi! Teşekkürler."
                else:
                    msg = "Bir hata oluştu, lütfen tekrar dene."

                chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=msg)
                logger.info(f"[+] AÇIKLAMA EKLENDİ | {user_name} ({user_id}) | Terim: {req.term} | Sonuç: {status}")
            except Exception as e:
                logger.error(f"[X] /acikla hatası: {e}", exc_info=True)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Açıklama eklenirken bir hata oluştu. Lütfen tekrar dene."
                )

        asyncio.run(process())

    # ── /glossary <terim_adi> ────────────────────────────────────

    @app.command("/glossary")
    def handle_glossary_command(ack, body):
        """Terim detayını gösterir (açıklamalar + faydalı butonları)."""
        ack()
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = body.get("text", "").strip()

        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        if not text:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text="Kullanım: `/glossary Docker`"
            )
            return

        detail = glossary_service.get_term_detail(text)
        if not detail:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text=f"*{text}* terimi sözlükte bulunamadı."
            )
            return

        term = detail["term"]
        definitions = detail["definitions"]

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{term['term']}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Kategori:* {term['category']}"},
                    {"type": "mrkdwn", "text": f"*Tür:* {term.get('term_type', 'term')}"},
                ]
            },
        ]

        if term.get("related_terms"):
            try:
                related = json.loads(term["related_terms"])
                if related:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*İlişkili:* {', '.join(related)}"}
                    })
            except (json.JSONDecodeError, TypeError):
                pass

        blocks.append({"type": "divider"})

        if definitions:
            for d in definitions:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"> {d['definition']}\n_— <@{d['contributor_id']}> | {d['helpful_count']} faydalı_"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Faydalı"},
                        "action_id": "glossary_helpful",
                        "value": d["id"],
                    }
                })
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Henüz açıklama eklenmemiş. `/acikla {term['term']} | açıklama` ile ilk sen ekle!"}
            })

        chat_manager.post_ephemeral(
            channel=channel_id, user=user_id,
            text=f"Terim: {term['term']}",
            blocks=blocks,
        )

    # ── Admin Onay/Red Butonları ─────────────────────────────────

    @app.action("glossary_admin_approve")
    def handle_admin_approve(ack, body):
        """Admin terimi onaylar."""
        ack()
        term_id = body["actions"][0]["value"]
        admin_id = body["user"]["id"]

        result = glossary_service.handle_admin_action(term_id, "approve")
        if result:
            logger.info(f"[+] ADMIN ONAY | Terim: {term_id} | Admin: {admin_id}")
            chat_manager.post_message(
                channel=body["channel"]["id"],
                text=f"<@{admin_id}> terimi onayladı.",
            )
        else:
            chat_manager.post_ephemeral(
                channel=body["channel"]["id"], user=admin_id,
                text="Terim bulunamadı veya zaten işlendi."
            )

    @app.action("glossary_admin_reject")
    def handle_admin_reject(ack, body):
        """Admin terimi reddeder."""
        ack()
        term_id = body["actions"][0]["value"]
        admin_id = body["user"]["id"]

        result = glossary_service.handle_admin_action(term_id, "reject")
        if result:
            logger.info(f"[-] ADMIN RED | Terim: {term_id} | Admin: {admin_id}")
            chat_manager.post_message(
                channel=body["channel"]["id"],
                text=f"<@{admin_id}> terimi reddetti.",
            )
        else:
            chat_manager.post_ephemeral(
                channel=body["channel"]["id"], user=admin_id,
                text="Terim bulunamadı veya zaten işlendi."
            )

    # ── Faydalı Butonu ───────────────────────────────────────────

    @app.action("glossary_helpful")
    def handle_helpful(ack, body):
        """Açıklamaya faydalı tepkisi (toggle)."""
        ack()
        definition_id = body["actions"][0]["value"]
        user_id = body["user"]["id"]

        added = glossary_service.toggle_helpful(definition_id, user_id)
        msg = "Faydalı tepkin eklendi!" if added else "Faydalı tepkin kaldırıldı."
        try:
            chat_manager.post_ephemeral(
                channel=body["channel"]["id"], user=user_id, text=msg
            )
        except Exception:
            pass  # Ephemeral başarısız olsa da tepki kaydedildi

    # ── Günlük Bülten Butonları ──────────────────────────────────

    @app.action("daily_term_knew")
    def handle_daily_knew(ack, body):
        """Biliyordum tepkisi."""
        ack()
        term_id = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        glossary_service.record_daily_reaction(term_id, user_id, "knew")
        try:
            chat_manager.post_ephemeral(
                channel=body["channel"]["id"], user=user_id,
                text="Biliyordum olarak kaydedildi!"
            )
        except Exception:
            pass

    @app.action("daily_term_didnt_know")
    def handle_daily_didnt_know(ack, body):
        """Bilmiyordum tepkisi."""
        ack()
        term_id = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        glossary_service.record_daily_reaction(term_id, user_id, "didnt_know")
        try:
            chat_manager.post_ephemeral(
                channel=body["channel"]["id"], user=user_id,
                text="Bilmiyordum olarak kaydedildi!"
            )
        except Exception:
            pass
