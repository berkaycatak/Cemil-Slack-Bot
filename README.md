# 🤖 Cemil Bot - Akıllı Topluluk Asistanı..

Cemil, Slack çalışma alanları için geliştirilmiş; yapay zeka destekli, modüler ve etkileşim odaklı bir topluluk botudur. Ekiplerin sosyalleşmesini, geri bildirim vermesini ve bilgiye hızlı erişmesini sağlar.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Slack Bolt](https://img.shields.io/badge/Slack-Bolt-green)
![Groq AI](https://img.shields.io/badge/AI-Groq-orange)

----

## ✨ Özellikler

### ☕ Kahve Eşleşmesi ve Networking
Çalışanların rastgele tanışıp sosyalleşmesi için akıllı eşleştirme sistemi.
- **Bekleme Havuzu:** `/kahve` yazan kişiler bir havuza alınır.
- **Otomatik Eşleşme:** 5 dakika içinde ikinci bir kişi gelirse otomatik eşleşme yapılır ve özel grup kurulur.
- **Buzkıran Sorular:** Cemil, sohbete yapay zeka tarafından üretilen eğlenceli bir giriş cümlesiyle başlar.
- **Zaman Ayarlı:** Sohbet kanalı 5 dakika sonra otomatik olarak arşivlendiği için "kısa bir kahve molası" konseptini korur.

### 🗳️ Gelişmiş Oylama Sistemi
Hızlı ve demokratik kararlar almak için ASCII grafikli anketler.
- **/oylama:** Adminler tarafından başlatılabilir.
- **Akıllı Oy:** "Toggle" desteği ile hatalı oyu geri alma ve değiştirme imkanı.
- **Anlık Grafikler:** Sonuçlar anlık olarak ASCII bar grafikleriyle gösterilir.
- **Süre Yönetimi:** Belirlenen süre sonunda otomatik kapanır.

### 🧠 Bilgi Küpü (RAG - Doküman Asistanı)
Şirket içi dökümanları okuyup soruları yanıtlayan yapay zeka modülü.
- **Format Desteği:** PDF, DOCX, TXT, MD, Excel (XLSX), CSV.
- **Halüsinasyon Koruması:** Sadece dökümandaki bilgiyi kullanır, dışarıdan uydurmaz.
- **Kaynak Gösterme:** Cevabın hangi dosyadan alındığını belirtir.
- **Komutlar:** `/sor [soru]` ve `/cemil-indeksle` (Admin).

### 🎂 Doğum Günü Kutlayıcısı
- Her sabah 09:00'da veritabanını kontrol eder.
- Doğum günü olan kişi varsa `#general` kanalına ASCII sanatıyla süslenmiş özel bir kutlama mesajı atar.

### 📮 Anonim Geri Bildirim Kutusu
- Çalışanların yönetim ekibine anonim olarak fikir ve şikayet iletmesini sağlar.
- **/geri-bildirim:** Mesajlar anonimleştirilip E-posta veya Slack DM üzerinden yöneticilere iletilir.

### 👤 Kullanıcı Yönetimi
- **/kayit:** Kullanıcılar kendi profillerini (Ad, Soyad, Departman, Doğum Tarihi) oluşturabilir/güncelleyebilir.
- **CSV Import:** Bot başlatılırken toplu kullanıcı listesi yüklenebilir.

---

## 🛠️ Kurulum ve Hazırlık

### 1. Gereksinimler
- Python 3.10+
- Slack Workspace (Admin yetkisi)
- Groq API Key (Yapay zeka için)
- Gmail Hesabı (Opsiyonel - Geri bildirim servisi için)

### 2. Projeyi Klonlayın ve Bağımlılıkları Yükleyin
```bash
git clone https://github.com/username/cemil-bot.git
cd cemil-bot
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Çevresel Değişkenler (.env)
`.env.example` dosyasını `.env` olarak kopyalayın ve içini doldurun:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
GROQ_API_KEY=gsk_...
SMTP_EMAIL=bot@gmail.com
SMTP_PASSWORD=...
ADMIN_CHANNEL_ID=C1234567
```

### 4. Slack Uygulama Ayarları (api.slack.com)
1. **Socket Mode:** Aktif edin.
2. **OAuth Scopes:** Aşağıdaki yetkileri ekleyin:
   - `chat:write`, `channels:read`, `channels:write`, `channels:manage`, `users:read`, `im:read`, `im:write`, `groups:write`, `mpim:write`, `commands`, `channels:history`, `groups:history`
3. **Slash Commands:** Aşağıdaki komutları oluşturun:
   - `/kahve`, `/oylama`, `/sor`, `/cemil-indeksle`, `/geri-bildirim`, `/profilim`, `/yardim-iste`, `/challenge`, `/cemil-health`, `/admin-istatistik`, `/admin-basarili-projeler`
4. **Interactive Components:** Aktif edin ve şu Action ID'leri ekleyin:
   - `challenge_join_button` - Challenge'a katıl butonu
   - `evaluate_challenge_button` - Projeyi değerlendir butonu
   - `join_coffee` - Kahve eşleşmesi butonu
   - `help_join_channel` - Yardım kanalına katıl butonu
   - `help_details` - Yardım detayları butonu
   - `poll_vote_0`, `poll_vote_1`, `poll_vote_2`, `poll_vote_3`, `poll_vote_4` - Oylama butonları
5. **Event Subscriptions:** Aşağıdaki event'leri subscribe edin:
   - `message.channels` - Challenge kanallarında "bitir" mesajı algılama için
   - `member_joined_channel` - Challenge kanallarına yetkisiz kullanıcı kontrolü için
   - `member_left_channel` - Değerlendirme kanalından ayrılan kullanıcı kontrolü için

---

## 🚀 Çalıştırma

Botu başlatmak için iki yöntem var:

**Yöntem 1: Hızlı Başlatma (Tavsiye Edilen)**
```bash
python3 -m src
```

**Yöntem 2: Doğrudan Dosya ile**
```bash
python3 src/bot.py
```

**İlk Başlatma:**
- `data/initial_users.csv` dosyası yoksa otomatik şablon oluşturulur.
- Varsa, bot veritabanını bu dosyadan doldurmak için onay ister.
- `knowledge_base/` klasörüne atılan dökümanlar otomatik indekslenir.

---

## 📖 Kullanım Kılavuzu

### 1. Kahve Molası
- `Genel` kanala veya herhangi bir yere: `/kahve` yazın.
- Bot size "İsteğiniz alındı" diyecek (bu mesajı sadece siz görürsünüz).
- 5 dakika içinde başka biri de `/kahve` yazarsa, bot sizi özel bir kanalda buluşturur!

### 2. Bilgi Sorma (RAG)
- `/sor Yıllık izin politikası nedir?`
- Cemil, `knowledge_base` klasöründeki PDF/Word dosyalarını tarayıp cevabı ve kaynağını size iletir.

### 3. Oylama (Sadece Admin)
- `/oylama 30 Cuma Etkinliği? | Bowling | Sinema | Piknik`
- 30 dakikalık bir anket başlatır.

### 4. Geri Bildirim
- `/geri-bildirim yemekhane Yemekler çok soğuk geliyor.`
- Bu mesaj anonim olarak adminlere iletilir.

# 🏆 Tournament System

Cemil artık topluluk içinde 8 kişilik mini turnuvalar düzenleyebilir.  
Sistem, random eşleşme, otomatik tur ilerlemesi ve haftalık puan tablosu içerir.


## 🎯 Genel Özellikler

- 8 kişilik turnuva sistemi
- Random Quarter Final eşleşmesi
- Otomatik Semi Final ve Final üretimi
- Haftalık leaderboard
- Katılım ve derece puanlama sistemi
- Mevcut Service + Repository mimarisine uygun yapı


## ⚙️ Komutlar

### Turnuva Başlatma
`/tournament start`
Yeni bir turnuva başlatır (maksimum 8 kişi).

### Turnuvaya Katılma
`/tournament join`

Aktif turnuvaya katılır.

### Bracket Oluşturma (Admin)
`/tournament bracket`
8 kişi dolduğunda Quarter Final eşleşmelerini oluşturur.

### Kazanan Belirleme (Admin)
`/tournament win <ROUND> <MATCH_NO> <WINNER_SLACK_ID>`


Round Kodları:
- `QF` → Quarter Final
- `SF` → Semi Final
- `F`  → Final


### Weekly Leaderboard
Haftalık puan tablosunu gösterir.


## 🏅 Puan Sistemi

| Placement       | Points |
|----------------|--------|
| Champion       | +10    |
| 2nd Place      | +5     |
| SF Loser       | +3     |
| Participation  | +1     |

Turnuva tamamlandığında puanlar otomatik yazılır.

---

## 🧠 Mimari

Tournament sistemi aşağıdaki katmanlarla geliştirilmiştir:

- `TournamentService`
- `TournamentRepository`
- `TournamentParticipantRepository`
- `TournamentMatchRepository`
- `TournamentPointsRepository`
- `tournament_handler.py`

Challenge sisteminden bağımsız çalışır.

## 📂 Klasör Yapısı
```
.
├── src/
│   ├── bot.py             # Ana başlangıç dosyası
│   ├── services/          # İş mantığı (Voting, Match, RAG vb.)
│   ├── clients/           # Dış servisler (Slack, Groq, DB)
│   ├── repositories/      # Veritabanı işlemleri
│   └── commands/          # Slack komut yöneticileri
├── data/                  # SQLite DB ve kullanıcı CSV'si
├── knowledge_base/        # RAG için dökümanlar
└── logs/                  # Bot logları
```

---

## ⚠️ Hata ve Destek
Bir sorunla karşılaşırsanız `logs/cemil_detailed.log` dosyasını kontrol edin.
Bot size "Teknik bir aksaklık yaşıyorum" diyorsa, API anahtarlarınızı ve internet bağlantınızı kontrol edin.

---
*Geliştirici Notu: Cemil, açık kaynak kodlu ve genişletilebilir bir yapıdadır. Katkılarınızı bekleriz!*
