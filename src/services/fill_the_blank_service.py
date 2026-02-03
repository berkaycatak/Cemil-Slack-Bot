import json
import random
import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.logger import logger
from src.repositories.fill_the_blank_repository import FillTheBlankRepository
from src.clients.songiq_client import SongIQClient
from src.clients.groq_client import GroqClient
from src.core.exceptions import ServiceError

class FillTheBlankService:
    """
    Şarkı sözü tamamlama oyunu için servis.
    """
    def __init__(self, 
                 repository: FillTheBlankRepository, 
                 songiq_client: SongIQClient,
                 groq_client: GroqClient):
        self.repository = repository
        self.songiq_client = songiq_client
        self.groq_client = groq_client

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Kategorileri getirir."""
        return await self.songiq_client.get_categories()

    async def start_game(self, user_id: str, channel_id: str, category_id: str) -> Dict[str, Any]:
        """
        Yeni bir oyun başlatır.
        1. Şarkı seçer.
        2. Önizlemeyi indirir.
        3. Sözleri transkribe eder.
        4. Boşlukları oluşturur.
        5. DB'ye kaydeder.
        """
        # Aktif oyun varsa önce onu bitir (opsiyonel, şimdilik aktif oyunu iptal edelim)
        active_game = self.repository.get_active_game_by_user(user_id)
        if active_game:
            self.repository.update(active_game["id"], {"status": "abandoned"})

        # 1. Şarkı seç
        song = await self.songiq_client.get_song(category_id)
        if not song:
            raise ServiceError("Bu kategoride şarkı bulunamadı.")

        preview_url = song.get("preview_url")
        if not preview_url:
            raise ServiceError("Şarkı önizlemesi bulunamadı.")

        # 2. Önizlemeyi indir
        audio_content = await self.songiq_client.download_preview(preview_url)
        if not audio_content:
            raise ServiceError("Şarkı önizlemesi indirilemedi.")

        # 3. Transkribe et
        try:
            full_lyrics = await self.groq_client.transcribe_audio(audio_content)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise ServiceError("Şarkı sözleri çözümlenemedi.")

        # 4. Boşlukları oluştur (LLM ile)
        system_prompt = """
        You are a game master for a "Fill in the Blanks" lyrics game.
        Your task is to take the provided song lyrics and replace 1 to 3 distinct words with underscores (_______).
        Rules:
        1. Select important words (nouns, verbs, adjectives) to blank out.
        2. Do NOT blank out common stop words like "the", "a", "is", "of" unless essential.
        3. Return a valid JSON object ONLY. No markdown, no explanation.
        JSON Format:
        {
            "blanked_lyrics": "The line with _______ words.",
            "missing_words": ["missing"]
        }
        """
        
        try:
            llm_response = await self.groq_client.quick_ask(system_prompt, full_lyrics)
            # Json parse etmeyi dene (bazen markdown block içinde gelebilir)
            clean_response = llm_response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1].strip()
            if clean_response.startswith("json"):
                clean_response = clean_response[4:].strip()
            
            game_data = json.loads(clean_response)
            blanked_lyrics = game_data.get("blanked_lyrics", full_lyrics)
            missing_words = game_data.get("missing_words", [])
            
            # Harf duyarlılığı sorun olmasın diye küçült
            missing_words_lower = [w.lower().strip() for w in missing_words]

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            # Fallback: Basit regex veya hata fırlatma
            raise ServiceError("Oyun içeriği oluşturulamadı.")

        # 5. DB'ye kaydet
        game_id = self.repository.create({
            "channel_id": channel_id,
            "user_id": user_id,
            "category_id": category_id,
            "song_title": song.get("title"),
            "song_artist": song.get("artist"),
            "original_lyrics": full_lyrics,
            "blanked_lyrics": blanked_lyrics,
            "correct_words": json.dumps(missing_words_lower),
            "status": "active"
        })

        return {
            "game_id": game_id,
            "title": song.get("title"),
            "artist": song.get("artist"),
            "preview_url": preview_url,
            "blanked_lyrics": blanked_lyrics,
            "audio_content": audio_content
        }

    def check_answer(self, user_id: str, user_answer: str) -> Dict[str, Any]:
        """
        Kullanıcının cevabını kontrol eder.
        """
        game = self.repository.get_active_game_by_user(user_id)
        if not game:
            return {"status": "no_game"}

        correct_words = json.loads(game["correct_words"])
        user_words = [w.lower().strip() for w in user_answer.split()]
        
        # Basit puanlama: Her doğru kelime için puan
        # Tam eşleşme mi arıyoruz yoksa içinde geçmesi yeterli mi?
        # Şimdilik basitçe: Eksik kelimelerden hangileri kullanıcının cevabında var?
        
        found_count = 0
        total_missing = len(correct_words)
        
        for w in correct_words:
            if w in user_words or any(w in uw for uw in user_words):
                 found_count += 1
        
        # Basit scor: (Bulunan / Toplam) * 100
        score = int((found_count / total_missing) * 100) if total_missing > 0 else 100
        
        # Oyunu bitir
        self.repository.update(game["id"], {
            "status": "completed", 
            "score": score
        })

        return {
            "status": "completed",
            "score": score,
            "correct_words": correct_words,
            "original_lyrics": game["original_lyrics"],
            "song_title": game["song_title"],
            "category_id": game["category_id"]
        }
