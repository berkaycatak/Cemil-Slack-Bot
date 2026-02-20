# src/services/ideathon_service.py
import asyncio
import random
from src.core.logger import logger

class IdeathonService:
    def __init__(self, repo, ai_service):
        self.repo = repo
        self.ai_service = ai_service  # main.py'den gelen GrokService buraya bağlanır

    async def create_ideathon_group(self, creator_id, channel_id, size):
        """Yeni bir takım oluşturma isteğini yönetir."""
        if not (2 <= size <= 5):
            return {"success": False, "message": "❌ Takım kapasitesi (siz dahil) 2 ile 5 arasında olmalıdır."}
        
        team = await self.repo.create_team(creator_id, channel_id, size)
        
        if not team:
            return {"success": False, "message": "❌ Takım oluşturulurken bir hata oluştu."}

        return {
            "success": True, 
            "message": f"🚀 <@{creator_id}> bir Ideathon başlattı! \n"
                       f"🆔 *Takım ID:* `{team['id']}`\n"
                       f"👥 *Kapasite:* {size} kişi\n"
                       f"👉 Katılmak için: `/ideathon join {team['id']}`"
        }

    async def join_group(self, user_id, team_id_or_channel):
        """Kullanıcıyı takıma ekler."""
        # Not: Repository'ne 'add_member' metodunu eklediğinde burayı bağlayabilirsin.
        return {"success": True, "message": f"✅ <@{user_id}> takıma başarıyla katıldı!"}

    async def start_session(self, channel_id):
        """Ideathon'u başlatır ve Grok'tan dinamik temalı özgün bir problem getirir."""
        team = await self.repo.get_team_by_channel(channel_id)
        if not team:
            return "❌ Bu kanalda aktif bir ideathon bulunamadı."

        # GENİŞLETİLMİŞ RASTGELE TEMA SEÇİMİ
        themes = [
            "Büyük Veri ve Analitik",
            "Görüntü İşleme ve AI",
            "Sürdürülebilir Enerji için Yazılım Çözümleri",
            "Blokzincir ve Güvenli Veri Paylaşımı",
            "Mikroservis Mimarisi ile E-Ticaret Optimizasyonu",
            "Yapay Zeka ve Etik", 
            "Eğitim Teknolojileri", 
            "Akıllı Şehirler", 
            "Veri Güvenliği"
        ]
        selected_theme = random.choice(themes)

        logger.info(f"[>] Grok'tan {selected_theme} temalı problem isteniyor...")

        # --- GERÇEK GROK ÇAĞRISI ---
        if self.ai_service:
            problem = await self.ai_service.generate_problem(theme=selected_theme)
        else:
            # AI servisi bağlı değilse yedek plan
            problem = f"⚠️ (Yedek Plan) {selected_theme} konusunda toplumu iyileştirecek bir yazılım çözümü geliştirin."
        
        # Repository'deki save_problem ile problem veritabanına işlenir ve status 'active' olur
        success = await self.repo.save_problem(team['id'], problem)
        
        if success:
            return (
                f"🏁 *Ideathon Başladı!* (Tema: {selected_theme})\n\n"
                f"{problem}\n\n"
                f"🚀 Başarılar Takım! Çözümünüzü geliştirin ve sunumunuz hazır olduğunda `/ideathon sunum <link>` ile paylaşın."
            )
        return "❌ Başlatma sırasında bir veritabanı hatası oluştu."

    async def submit_presentation(self, channel_id, user_id, link):
        """Sunum linkini kaydeder."""
        team = await self.repo.get_team_by_channel(channel_id)
        if not team:
            return "❌ Bu kanalda aktif bir ideathon bulunamadı."
        
        success = await self.repo.save_presentation(team['id'], link)
        if success:
            return f"✅ <@{user_id}> projesini teslim etti! \n🔗 *Sunum Linki:* {link}\n⭐ Şimdi takım üyeleri `/ideathon puan <1-5>` ile oylama yapabilir."
        return "❌ Sunum kaydedilemedi."

    async def finalize_and_score(self, channel_id):
        """Ideathon'u bitirir ve ortalama puanı raporlar."""
        team = await self.repo.get_team_by_channel(channel_id)
        if not team:
            return "❌ Bitirilecek aktif bir süreç bulunamadı."

        avg_score = await self.repo.get_average_score(team['id'])
        
        return (
            f"🎊 *Ideathon Süreci Tamamlandı!*\n\n"
            f"📊 *Takım Skoru:* `{avg_score:.2f}/5` \n"
            f"👏 Emek veren tüm bursiyerleri tebrik ederiz! Yeni bir maraton için `/ideathon kur` yazabilirsiniz."
        )