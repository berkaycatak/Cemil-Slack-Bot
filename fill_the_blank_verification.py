
import asyncio
import os
from dotenv import load_dotenv

# Environment variables
load_dotenv()

from src.clients.songiq_client import SongIQClient
from src.clients.groq_client import GroqClient
from src.core.logger import logger

async def main():
    print("🚀 Başlatılıyor...")
    
    # 1. Clients
    songiq = SongIQClient()
    groq = GroqClient()
    
    # 2. Categories
    print("\n📂 Kategoriler çekiliyor...")
    cats = await songiq.get_categories()
    print(f"✅ {len(cats)} kategori bulundu: {[c['document_id'] for c in cats]}")
    
    if not cats:
        print("❌ Kategori bulunamadı!")
        return

    cat_id = cats[0]['document_id'] # İlk kategoriyi al (örn. en_pop)
    
    # 3. Song
    print(f"\n🎵 Şarkı çekiliyor ({cat_id})...")
    song = await songiq.get_song(cat_id)
    
    if not song:
        print("❌ Şarkı bulunamadı!")
        return
        
    print(f"✅ Şarkı: {song['title']} - {song['artist']}")
    print(f"🔗 Preview: {song['preview_url']}")
    
    # 4. Download Preview
    print("\n⬇️ Önizleme indiriliyor...")
    audio_data = await songiq.download_preview(song['preview_url'])
    
    if not audio_data:
        print("❌ Önizleme indirilemedi!")
        return
        
    print(f"✅ İndirildi: {len(audio_data)} bytes")
    
    # 5. Transcribe (Groq Whisper)
    print("\n🗣️ Transkript ediliyor (Distil-Whisper)...")
    try:
        lyrics = await groq.transcribe_audio(audio_data, filename="test_song.mp3")
        print(f"✅ Lyrics:\n---\n{lyrics}\n---")
    except Exception as e:
        print(f"❌ Transkripsiyon hatası: {e}")
        return

    # 6. Blanking (LLM)
    print("\n🧠 Boşluklar oluşturuluyor (LLM)...")
    system_prompt = """
    You are a game master for a "Fill in the Blanks" lyrics game.
    Your task is to take the provided song lyrics and replace 1 to 3 distinct words with underscores (_______).
    Rules:
    1. Select important words (nouns, verbs, adjectives) to blank out.
    2. Do NOT blank out common stop words like "the", "a", "is", "of" unless essential.
    3. Return a valid JSON object ONLY.
    JSON Format:
    {
        "blanked_lyrics": "The line with _______ words.",
        "missing_words": ["missing"]
    }
    """
    
    try:
        llm_response = await groq.quick_ask(system_prompt, lyrics)
        print(f"✅ LLM Yanıtı:\n{llm_response}")
    except Exception as e:
        print(f"❌ LLM hatası: {e}")

    await groq.close()
    print("\n✨ Test Tamamlandı.")

if __name__ == "__main__":
    asyncio.run(main())
