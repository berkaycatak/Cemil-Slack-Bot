import httpx
from typing import List, Dict, Any, Optional
from src.core.logger import logger
from src.core.singleton import SingletonMeta

class SongIQClient(metaclass=SingletonMeta):
    """
    SongIQ API istemcisi.
    Kategorileri ve şarkıları çeker.
    """
    BASE_URL = "https://api.songiqapp.com/api"

    async def get_categories(self, language: str = "en") -> List[Dict[str, Any]]:
        """Kategorileri getirir."""
        url = f"{self.BASE_URL}/categories"
        params = {"language": language}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[X] SongIQ categories hatası: {e}")
            return []

    async def get_song(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirtilen kategoriden rastgele bir şarkı getirir.
        limit=1 ve withPreview=1 parametreleri kullanılır.
        """
        url = f"{self.BASE_URL}/songs"
        params = {
            "category_id": category_id,
            "limit": 1,
            "withPreview": 1
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                songs = response.json()
                if songs and len(songs) > 0:
                    return songs[0]
                return None
        except Exception as e:
            logger.error(f"[X] SongIQ song hatası: {e}")
            return None

    async def download_preview(self, preview_url: str) -> Optional[bytes]:
        """Şarkı önizlemesini indirir (bytes olarak döner)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(preview_url, timeout=15.0)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"[X] Preview indirme hatası: {e}")
            return None
