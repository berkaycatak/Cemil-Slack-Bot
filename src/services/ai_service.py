import httpx
import json
from src.core.logger import logger
from src.core.settings import get_settings


class GrokService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.grok_api_key
        self.base_url = "https://api.x.ai/v1/chat/completions"

    async def generate_problem(self, theme: str = "Yazılım Geliştirme ve Yapay Zeka"):
        """
        Grok'u kıdemli bir yazılım mimarı rolüne sokarak özgün,
        teknik ve zorlayıcı bir Ideathon problemi üretir.
        """

        prompt = f"""
        Sen Cemil Bot'un beynisin ve dünya çapında bir Senior Software Architect (Kıdemli Yazılım Mimarı) rolündesin. 
        Bilgisayar mühendisliği öğrencileri için "{theme}" temalı bir Ideathon problemi üretmeni istiyorum.
        
        Senden beklenen yanıt formatı ve içeriği:
        
        1. 🚀 **BAŞLIK**: Problem için etkileyici ve teknik bir başlık.
        2. 🎯 **SORUN TANIMI**: Gerçek dünya senaryosuna dayanan, karmaşık ama 48 saatte konsepti oluşturulabilecek bir sorun.
        3. 🛠️ **TEKNİK BEKLENTİLER**: 
           - Kullanılması önerilen modern teknolojiler (Python, FastAPI, React, PostgreSQL, Docker, AI kütüphaneleri vb.).
           - Mimari bir öneri (Mikroservis, Event-driven vb.).
        4. 📦 **TESLİMAT ÇIKTILARI**: Takımın sunumunda mutlaka olması gerekenler (Sistem şeması, Veritabanı tasarımı, Prototip akışı).
        5. 💡 **KRİTİK İPUCU**: Çözümde fark yaratacak teknik bir dokunuş önerisi.
        
        Kısıtlamalar:
        - Dil: Tamamen Türkçe olmalı.
        - Zorluk Seviyesi: Orta-İleri (Bilgisayar Mühendisliği bursiyerlerine uygun).
        - Format: Yanıtı Slack üzerinde çok şık görünecek şekilde zengin Markdown kullanarak dön.
        
        Lütfen doğrudan problemi anlatmaya başla, "Tabii, işte probleminiz:" gibi giriş cümleleri kurma.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "grok-2-1212",
            "messages": [
                {
                    "role": "system",
                    "content": "Sen yaratıcı ve teknik bir teknoloji mentörüsün.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
        }

        try:
            logger.info(f"[AI] Grok'tan {theme} temalı problem üretiliyor...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url, headers=headers, json=data, timeout=60.0
                )
                response.raise_for_status()
                result = response.json()

                problem_text = result["choices"][0]["message"]["content"]
                logger.info("[AI] Problem başarıyla üretildi.")
                return problem_text

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[X] Grok API HTTP Hatası ({e.response.status_code}): {e.response.text}"
            )
            return self._get_fallback_problem(theme)
        except Exception as e:
            logger.error(f"[X] Grok Servis Hatası: {e}")
            return self._get_fallback_problem(theme)

    def _get_fallback_problem(self, theme):
        """API hatası durumunda dönecek güvenli yedek problem."""
        return (
            f"⚠️ *Grok şu an meşgul, ama Cemil sizin için bir fikir buldu!*\n\n"
            f"*Tema:* {theme}\n"
            f"*Problem:* Şehir içi ulaşımı ve karbon ayak izini optimize eden bir lojistik yönetim paneli tasarlayın.\n"
            f"Lütfen bağlantıyı kontrol edin ve tekrar deneyin."
        )
