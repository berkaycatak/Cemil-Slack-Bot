from slack_bolt import App
import asyncio
from src.core.logger import logger


def setup_ideathon_handlers(app: App, ideathon_service, chat_manager):
    """
    Ideathon komutlarını (kur, join, baslat, sunum, puan, bitir)
    Slack uygulamasına kaydeder.
    """

    @app.command("/ideathon")
    def handle_ideathon(ack, body):
        ack()

        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text_parts = body.get("text", "").strip().split()

        if not text_parts:
            chat_manager.post_ephemeral(
                channel_id,
                user_id,
                "💡 *Cemil Ideathon Komutları:*\n\n"
                "• `/ideathon kur <kişi_sayısı>` - Yeni takım oluştur (2-5 kişi)\n"
                "• `/ideathon join <takım_id>` - Mevcut bir takıma katıl\n"
                "• `/ideathon baslat` - Grok'tan sorunu getir ve maratonu başlat\n"
                "• `/ideathon sunum <link>` - Proje sunum linkini teslim et\n"
                "• `/ideathon puan <1-5>` - Takım projelerine puan ver\n"
                "• `/ideathon bitir` - Süreci tamamla ve karne sonucunu gör",
            )
            return

        subcommand = text_parts[0].lower()

        if subcommand == "kur":
            try:
                size = int(text_parts[1]) if len(text_parts) > 1 else 3
                result = asyncio.run(
                    ideathon_service.create_ideathon_group(user_id, channel_id, size)
                )
                chat_manager.post_message(channel_id, result["message"])
            except ValueError:
                chat_manager.post_ephemeral(
                    channel_id,
                    user_id,
                    "❌ Lütfen geçerli bir sayı girin. Örn: `/ideathon kur 3`",
                )

        elif subcommand == "join":
            team_id = text_parts[1] if len(text_parts) > 1 else ""
            if not team_id:
                chat_manager.post_ephemeral(
                    channel_id, user_id, "❌ Lütfen bir Takım ID girin."
                )
                return
            result = asyncio.run(ideathon_service.join_group(user_id, team_id))
            chat_manager.post_message(channel_id, result["message"])

        elif subcommand == "baslat":
            chat_manager.post_message(
                channel_id,
                "🧠 *Cemil, Grok'a bağlanıp size özel bir problem hazırlıyor...*",
            )
            result = asyncio.run(ideathon_service.start_session(channel_id))
            chat_manager.post_message(channel_id, result)

        elif subcommand == "sunum":
            link = text_parts[1] if len(text_parts) > 1 else ""
            if not link.startswith("http"):
                chat_manager.post_ephemeral(
                    channel_id, user_id, "❌ Lütfen geçerli bir URL girin."
                )
                return
            result = asyncio.run(
                ideathon_service.submit_presentation(channel_id, user_id, link)
            )
            chat_manager.post_message(channel_id, result)

        elif subcommand == "puan":
            try:
                score = int(text_parts[1])
                if not (1 <= score <= 5):
                    raise ValueError()

                team = asyncio.run(
                    ideathon_service.repo.get_team_by_channel(channel_id)
                )
                if team:
                    asyncio.run(
                        ideathon_service.repo.add_score(team["id"], user_id, score)
                    )
                    chat_manager.post_message(
                        channel_id,
                        f"⭐ <@{user_id}> bu projeye *{score}/5* puan verdi!",
                    )
                else:
                    chat_manager.post_ephemeral(
                        channel_id,
                        user_id,
                        "❌ Puan vermek için aktif bir ideathon kanalında olmalısınız.",
                    )
            except:
                chat_manager.post_ephemeral(
                    channel_id, user_id, "❌ Lütfen 1-5 arasında bir tam sayı girin."
                )

        elif subcommand == "bitir":
            result = asyncio.run(ideathon_service.finalize_and_score(channel_id))
            chat_manager.post_message(channel_id, result)

        else:
            chat_manager.post_ephemeral(
                channel_id, user_id, f"❌ Bilinmeyen komut: `{subcommand}`"
            )
