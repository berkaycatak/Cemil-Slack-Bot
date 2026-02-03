from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class FillTheBlankRepository(BaseRepository):
    """
    fill_the_blank_games tablosu için repository.
    """
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "fill_the_blank_games")
    
    def get_active_game_by_user(self, user_id: str):
        """Kullanıcının aktif oyununu getirir."""
        games = self.list({
            "user_id": user_id,
            "status": "active"
        })
        return games[0] if games else None
