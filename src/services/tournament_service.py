"""
Tournament service (MVP).
- Uses SQLite via DatabaseClient
- Minimal tournament flow:
  start -> join (max 8) -> bracket (QF) -> win (QF/SF/F) -> leaderboard (weekly)
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.core.logger import logger
from src.core.settings import get_settings
from src.clients import DatabaseClient

from src.repositories.tournament_repository import TournamentRepository
from src.repositories.tournament_participant_repository import TournamentParticipantRepository
from src.repositories.tournament_match_repository import TournamentMatchRepository
from src.repositories.tournament_points_repository import TournamentPointsRepository


class TournamentService:

    def __init__(self, db_path: str = None):
        """
        db_path verilirse settings'e ihtiyaç duymadan test edilebilir.
        Üretimde db_path None kalır ve settings.database_path kullanılır.
        """
        if db_path is None:
            settings = get_settings()
            db_path = settings.database_path

        self.db_client = DatabaseClient(db_path=db_path)

        self.tournament_repo = TournamentRepository(self.db_client)
        self.participant_repo = TournamentParticipantRepository(self.db_client)
        self.match_repo = TournamentMatchRepository(self.db_client)
        self.points_repo = TournamentPointsRepository(self.db_client)
    # -----------------------
    # Helpers
    # -----------------------

    def _week_start(self) -> str:
        """
        Haftalık leaderboard için haftanın başlangıcı (Pazartesi).
        DB’de 'YYYY-MM-DD' olarak tutulur.
        """
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat()

    def _get_active_tournament(self) -> Optional[Dict[str, Any]]:
        """
        MVP: En son OPEN turnuvayı tercih eder.
        Eğer OPEN yoksa IN_PROGRESS olanı döndürür.
        """
        open_one = self.tournament_repo.get_open_tournament()
        if open_one:
            return open_one

        query = "SELECT * FROM tournaments WHERE status = 'IN_PROGRESS' ORDER BY created_at DESC LIMIT 1"
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None

    def _matches_exist(self, tournament_id: str) -> bool:
        query = "SELECT 1 FROM tournament_matches WHERE tournament_id = ? LIMIT 1"
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id,))
            return cursor.fetchone() is not None

    def _create_match(self, tournament_id: str, round_code: str, match_no: int, p1: str, p2: str) -> None:
        match_id = uuid.uuid4().hex
        query = """
            INSERT INTO tournament_matches
            (id, tournament_id, round, match_no, player1_id, player2_id, winner_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (match_id, tournament_id, round_code, match_no, p1, p2))
            conn.commit()

    def _round_complete(self, tournament_id: str, round_code: str) -> bool:
        query = """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN winner_id IS NOT NULL THEN 1 ELSE 0 END) AS decided
            FROM tournament_matches
            WHERE tournament_id = ? AND round = ?
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id, round_code))
            row = cursor.fetchone()
            if not row or row["total"] == 0:
                return False
            return int(row["decided"]) == int(row["total"])

    def _round_winners(self, tournament_id: str, round_code: str) -> List[str]:
        query = """
            SELECT winner_id
            FROM tournament_matches
            WHERE tournament_id = ? AND round = ?
            ORDER BY match_no ASC
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id, round_code))
            rows = cursor.fetchall()
            return [r["winner_id"] for r in rows if r["winner_id"]]

    def _sf_losers(self, tournament_id: str) -> List[str]:
        """
        SF maçlarından kaybedenleri döndürür.
        (MVP: üçüncülük maçı yok; iki SF kaybedenine de 3 puan veriyoruz.)
        """
        query = """
            SELECT player1_id, player2_id, winner_id
            FROM tournament_matches
            WHERE tournament_id = ? AND round = 'SF'
            ORDER BY match_no ASC
        """
        losers: List[str] = []
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id,))
            rows = cursor.fetchall()
            for r in rows:
                w = r["winner_id"]
                if not w:
                    continue
                p1, p2 = r["player1_id"], r["player2_id"]
                loser = p2 if w == p1 else p1
                losers.append(loser)
        return losers

    # -----------------------
    # Public API used by handler
    # -----------------------

    def start(self, created_by: str) -> Dict[str, Any]:
        existing = self.tournament_repo.get_open_tournament()
        if existing:
            return {
                "success": True,
                "message": f"ℹ️ An open tournament already exists. (id: {existing['id']})"
            }

        tid = uuid.uuid4().hex
        query = """
            INSERT INTO tournaments (id, created_by, status, max_participants, created_at, updated_at)
            VALUES (?, ?, 'OPEN', 8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tid, created_by))
            conn.commit()

        return {"success": True, "message": f"✅ Tournament started! ID: {tid}\nUse `/tournament join` to participate (max 8)."}

    def join(self, user_id: str) -> Dict[str, Any]:
        t = self.tournament_repo.get_open_tournament()
        if not t:
            return {"success": False, "message": "❌ No open tournament. Ask an admin to run `/tournament start`."}

        tournament_id = t["id"]
        max_p = int(t.get("max_participants") or 8)

        if self.participant_repo.is_joined(tournament_id, user_id):
            return {"success": True, "message": "ℹ️ You already joined this tournament."}

        current = self.participant_repo.count_participants(tournament_id)
        if current >= max_p:
            return {"success": False, "message": "❌ Tournament is full (8/8)."}

        pid = uuid.uuid4().hex
        query = """
            INSERT INTO tournament_participants (id, tournament_id, user_id, joined_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pid, tournament_id, user_id))
            conn.commit()

        # Participation point (+1)
        self.points_repo.add_points(self._week_start(), user_id, 1)

        new_count = self.participant_repo.count_participants(tournament_id)
        if new_count == max_p:
            return {
                "success": True,
                "message": f"✅ Joined! ({new_count}/{max_p})\n🎯 Tournament is now full. Admin can run `/tournament bracket`."
            }
        return {"success": True, "message": f"✅ Joined! ({new_count}/{max_p})"}

    def create_bracket(self, admin_id: str) -> Dict[str, Any]:
        t = self.tournament_repo.get_open_tournament()
        if not t:
            return {"success": False, "message": "❌ No open tournament to create a bracket for."}

        tournament_id = t["id"]
        max_p = int(t.get("max_participants") or 8)
        participants = self.participant_repo.list_participants(tournament_id)
        if len(participants) < max_p:
            return {"success": False, "message": f"❌ Not enough participants. ({len(participants)}/{max_p})"}

        if self._matches_exist(tournament_id):
            return {"success": True, "message": "ℹ️ Bracket already exists for this tournament."}

        user_ids = [p["user_id"] for p in participants]
        random.shuffle(user_ids)

        # QF: 4 matches
        pairs = [(user_ids[i], user_ids[i + 1]) for i in range(0, 8, 2)]
        for idx, (p1, p2) in enumerate(pairs, start=1):
            self._create_match(tournament_id, "QF", idx, p1, p2)

        # Tournament now in progress
        self.tournament_repo.set_status(tournament_id, "IN_PROGRESS")

        lines = ["✅ Bracket created (QF):"]
        for i, (p1, p2) in enumerate(pairs, start=1):
            lines.append(f"- QF {i}: {p1} vs {p2}")
        lines.append("\nAdmin can set winners with:")
        lines.append("`/tournament win QF <match_no> <winner_slack_id>`")

        return {"success": True, "message": "\n".join(lines)}

    def set_winner(self, admin_id: str, round_code: str, match_no: int, winner_id: str) -> Dict[str, Any]:
        t = self._get_active_tournament()
        if not t:
            return {"success": False, "message": "❌ No active tournament found."}

        tournament_id = t["id"]

        # Find match by tournament + round + match_no
        query = """
            SELECT * FROM tournament_matches
            WHERE tournament_id = ? AND round = ? AND match_no = ?
            LIMIT 1
        """
        with self.db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tournament_id, round_code, match_no))
            row = cursor.fetchone()
            match = dict(row) if row else None

        if not match:
            return {"success": False, "message": f"❌ Match not found: {round_code} {match_no}"}

        p1, p2 = match["player1_id"], match["player2_id"]
        if winner_id not in (p1, p2):
            return {"success": False, "message": "❌ winner_slack_id must be one of the match players."}

        if match.get("winner_id"):
            return {"success": True, "message": "ℹ️ This match already has a winner."}

        self.match_repo.set_winner(match["id"], winner_id)

        msg_lines = [f"✅ Winner saved: {round_code} {match_no} -> {winner_id}"]

        # If round completed, create next round
        if self._round_complete(tournament_id, round_code):
            if round_code == "QF":
                winners = self._round_winners(tournament_id, "QF")
                if len(winners) == 4:
                    # Create SF (2 matches)
                    self._create_match(tournament_id, "SF", 1, winners[0], winners[1])
                    self._create_match(tournament_id, "SF", 2, winners[2], winners[3])
                    msg_lines.append("🎯 QF completed. SF matches created.")
                    msg_lines.append("Use: `/tournament win SF <match_no> <winner_slack_id>`")

            elif round_code == "SF":
                winners = self._round_winners(tournament_id, "SF")
                if len(winners) == 2:
                    # Create Final (1 match)
                    self._create_match(tournament_id, "F", 1, winners[0], winners[1])
                    msg_lines.append("🏁 SF completed. Final match created.")
                    msg_lines.append("Use: `/tournament win F 1 <winner_slack_id>`")

            elif round_code == "F":
                # Final completed => finalize & award points
                final_query = """
                    SELECT player1_id, player2_id, winner_id
                    FROM tournament_matches
                    WHERE tournament_id = ? AND round = 'F' AND match_no = 1
                    LIMIT 1
                """
                with self.db_client.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(final_query, (tournament_id,))
                    fr = cursor.fetchone()

                if fr and fr["winner_id"]:
                    champion = fr["winner_id"]
                    runner_up = fr["player2_id"] if champion == fr["player1_id"] else fr["player1_id"]

                    week = self._week_start()
                    # 1st: +10
                    self.points_repo.add_points(week, champion, 10)
                    # 2nd: +5
                    self.points_repo.add_points(week, runner_up, 5)
                    # 3rd (MVP): both SF losers +3
                    for loser in self._sf_losers(tournament_id):
                        self.points_repo.add_points(week, loser, 3)

                    self.tournament_repo.set_status(tournament_id, "FINISHED")
                    msg_lines.append("🏆 Tournament finished! Points awarded.")
                    msg_lines.append(f"1st: {champion} (+10), 2nd: {runner_up} (+5), SF losers (+3 each)")

        return {"success": True, "message": "\n".join(msg_lines)}

    def get_weekly_leaderboard(self) -> Dict[str, Any]:
        week = self._week_start()
        rows = self.points_repo.get_leaderboard(week_start=week, limit=10)

        if not rows:
            return {"success": True, "message": "📊 Weekly leaderboard is empty (no points yet)."}

        lines = [f"📊 Weekly Leaderboard (week starting {week})"]
        for i, r in enumerate(rows, start=1):
            lines.append(f"{i}. {r['user_id']} — {r['points']} pts")

        return {"success": True, "message": "\n".join(lines)}