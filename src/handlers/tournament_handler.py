"""
Tournament command handlers.
"""

from slack_bolt import App
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.commands import ChatManager
from src.repositories import UserRepository


def setup_tournament_handlers(
    app: App,
    tournament_service,
    chat_manager: ChatManager,
    user_repo: UserRepository
):
    settings = get_settings()
    rate_limiter = get_rate_limiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window
    )

    @app.command("/tournament")
    def handle_tournament_command(ack, body):
        ack()
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = (body.get("text") or "").strip()

        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        if not text:
            chat_manager.post_ephemeral(
                channel=channel_id,
                user=user_id,
                text=(
                    "🏆 *Tournament Commands (MVP)*\n\n"
                    "`/tournament start` - (Admin) Start a new tournament (max 8)\n"
                    "`/tournament join` - Join the open tournament\n"
                    "`/tournament bracket` - (Admin) Generate QF bracket\n"
                    "`/tournament win <QF|SF|F> <match_no> <winner_slack_id>` - (Admin) Set match winner\n"
                    "`/tournament leaderboard` - Show weekly leaderboard\n"
                )
            )
            return

        parts = text.split()
        sub = parts[0].lower()
        args = parts[1:]

        try:
            user_data = user_repo.get_by_slack_id(user_id)
            user_name = user_data.get("full_name", user_id) if user_data else user_id
        except Exception:
            user_name = user_id

        logger.info(f"[>] /tournament {sub} | {user_name} ({user_id})")

        def require_admin() -> bool:
            if user_id != settings.admin_slack_id:
                chat_manager.post_ephemeral(
                    channel=channel_id,
                    user=user_id,
                    text="⛔ This command is admin-only."
                )
                return False
            return True

        if sub == "start":
            if not require_admin():
                return
            result = tournament_service.start(created_by=user_id)
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=result.get("message", "OK"))

        elif sub == "join":
            result = tournament_service.join(user_id=user_id)
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=result.get("message", "OK"))

        elif sub == "bracket":
            if not require_admin():
                return
            result = tournament_service.create_bracket(admin_id=user_id)
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=result.get("message", "OK"))

        elif sub == "win":
            if not require_admin():
                return
            if len(args) != 3:
                chat_manager.post_ephemeral(
                    channel=channel_id,
                    user=user_id,
                    text="❌ Format: `/tournament win <QF|SF|F> <match_no> <winner_slack_id>`"
                )
                return
            round_code, match_no_str, winner_id = args
            try:
                match_no = int(match_no_str)
            except ValueError:
                chat_manager.post_ephemeral(channel=channel_id, user=user_id, text="❌ match_no must be a number.")
                return

            result = tournament_service.set_winner(
                admin_id=user_id,
                round_code=round_code.upper(),
                match_no=match_no,
                winner_id=winner_id
            )
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=result.get("message", "OK"))
