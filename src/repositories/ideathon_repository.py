import uuid
import json
from src.core.logger import logger

class IdeathonRepository:
    def __init__(self, db_session):
        # db_session burada senin db_client nesnen olacak
        self.db = db_session 

    async def create_team(self, creator_id, channel_id, team_size):
        """Yeni bir ideathon takımı oluşturur."""
        team_id = f"IDE-{uuid.uuid4().hex[:6].upper()}"
        
        query = """
            INSERT INTO ideathon_teams (id, creator_id, channel_id, team_size, status)
            VALUES (?, ?, ?, ?, 'pending')
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (team_id, creator_id, channel_id, team_size))
            conn.commit()
            
            return {
                "id": team_id,
                "creator_id": creator_id,
                "channel_id": channel_id,
                "team_size": team_size,
                "status": "pending"
            }
        except Exception as e:
            logger.error(f"[X] Team oluşturma hatası: {e}")
            return None

    async def get_team_by_channel(self, channel_id):
        """Kanal ID'sine göre aktif takımı getirir."""
        query = "SELECT * FROM ideathon_teams WHERE channel_id = ? AND status != 'finished'"
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (channel_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def save_problem(self, team_id, problem_statement):
        """Grok'tan gelen soruyu takıma kaydeder ve durumu active yapar."""
        query = "UPDATE ideathon_teams SET problem_statement = ?, status = 'active' WHERE id = ?"
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (problem_statement, team_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[X] Problem kaydetme hatası: {e}")
            return False

    async def save_presentation(self, team_id, link):
        """Sunum linkini günceller."""
        query = "UPDATE ideathon_teams SET presentation_link = ? WHERE id = ?"
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (link, team_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[X] Sunum kaydetme hatası: {e}")
            return False

    async def add_score(self, team_id, voter_id, score):
        """Verilen puanı kaydeder."""
        query = """
            INSERT INTO ideathon_scores (team_id, voter_id, score)
            VALUES (?, ?, ?)
         Chad   """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (team_id, voter_id, score))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[X] Puan kaydetme hatası: {e}")
            return False

    async def get_average_score(self, team_id):
        """Takımın ortalama puanını hesaplar."""
        query = "SELECT AVG(score) as avg_score FROM ideathon_scores WHERE team_id = ?"
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (team_id,))
        result = cursor.fetchone()
        return result["avg_score"] if result and result["avg_score"] else 0