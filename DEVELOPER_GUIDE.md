# Cemil Bot - Gelistirici Rehberi (Developer Guide)

> Bu belge, Cemil Bot projesine yeni ozellik veya slash komutu eklemek isteyen gelistiriciler icin yazilmistir.
> Projeyi hic bilmeyen biri bile bu belgeyi okudugunda **nereye, nasil ve hangi kurallara uyarak** kod eklemesi gerektigini anlayabilir.

---

## Icindekiler

1. [Proje Hakkinda](#1-proje-hakkinda)
2. [Teknoloji Yigini (Tech Stack)](#2-teknoloji-yigini-tech-stack)
3. [Klasor Yapisi ve Katmanlar](#3-klasor-yapisi-ve-katmanlar)
4. [Katman Detaylari](#4-katman-detaylari)
   - 4.1 [src/core/ - Altyapi Katmani](#41-srccore---altyapi-katmani)
   - 4.2 [src/clients/ - Dis Servis Baglantilari](#42-srcclients---dis-servis-baglantilari)
   - 4.3 [src/commands/ - Slack API Wrapper'lari](#43-srccommands---slack-api-wrapperlari)
   - 4.4 [src/repositories/ - Veritabani Erisim Katmani](#44-srcrepositories---veritabani-erisim-katmani)
   - 4.5 [src/services/ - Is Mantigi Katmani](#45-srcservices---is-mantigi-katmani)
   - 4.6 [src/handlers/ - Slash Komut Yoneticileri](#46-srchandlers---slash-komut-yoneticileri)
5. [Veri Akisi (Data Flow)](#5-veri-akisi-data-flow)
6. [Yeni Ozellik Ekleme Rehberi (Adim Adim)](#6-yeni-ozellik-ekleme-rehberi-adim-adim)
7. [Kodlama Kurallari ve Konvansiyonlar](#7-kodlama-kurallari-ve-konvansiyonlar)
8. [Kayit (Registration) Kontrol Listesi](#8-kayit-registration-kontrol-listesi)
9. [Hata Yonetimi Kurallari](#9-hata-yonetimi-kurallari)
10. [Test Yazma Rehberi](#10-test-yazma-rehberi)
11. [PR (Pull Request) Kontrol Listesi](#11-pr-pull-request-kontrol-listesi)

---

## 1. Proje Hakkinda

**Cemil Bot**, "Yapay Zeka ve Teknoloji Akademisi" toplulugunun Slack uzerindeki etkilesimini artirmak icin gelistirilmis bir topluluk yonetim botudur.

**Ne yapar?**
- Kahve eslesmesi (coffee roulette) ile topluluk uyelerini tanistirir
- RAG tabanli bilgi bankasi ile dokumanlara soru sorma imkani saglar
- Mini-hackathon (challenge hub) sistemi ile takim calismasini destekler
- Oylama, geri bildirim, yardim kanallari ve profil yonetimi sunar

**Platform:** Slack (Slack Bolt framework + Socket Mode)
**Dil:** Python 3.10+

---

## 2. Teknoloji Yigini (Tech Stack)

| Teknoloji | Versiyon/Detay | Nerede Kullaniliyor | Neden Secildi |
|-----------|---------------|---------------------|---------------|
| **Python** | 3.10+ | Tum proje | Ana gelistirme dili |
| **Slack Bolt** | slack-bolt | Bot framework (`src/bot.py`) | Slack'in resmi Python bot framework'u |
| **Slack SDK** | slack-sdk | API cagrilari (`src/commands/`) | Slack Web API erisimi |
| **SQLite** | sqlite3 (built-in) | Veritabani (`src/clients/database_client.py`) | Hafif, dosya tabanli, sunucu gerektirmez |
| **Pydantic** | pydantic + pydantic-settings | Konfigurasyon ve validation (`src/core/`) | Tip guvenligi ve environment variable yonetimi |
| **Groq API** | groq (async) | LLM islemleri (`src/clients/groq_client.py`) | Hizli ve ucretsiz LLM API |
| **FAISS** | faiss-cpu | Vektor arama (`src/clients/vector_client.py`) | Hizli similarity search, GPU gerektirmez |
| **SentenceTransformers** | all-MiniLM-L6-v2 | Embedding olusturma (`src/clients/vector_client.py`) | Hafif, hizli embedding modeli |
| **APScheduler** | BackgroundScheduler | Zamanli gorevler (`src/clients/cron_client.py`) | Background job scheduling |
| **python-dotenv** | dotenv | Environment variable (`src/__main__.py`) | `.env` dosyasindan yapilandirma yukleme |

---

## 3. Klasor Yapisi ve Katmanlar

```
Cemil_Bot/
│
├── src/                          # Ana kaynak kodu
│   ├── __init__.py               # Bos (package marker)
│   ├── __main__.py               # GIRIS NOKTASI - Bot baslatma, shutdown, migration
│   ├── bot.py                    # TUM BILESENLERI BIRLESTIRIR - Client, repo, service, handler kayitlari
│   │
│   ├── core/                     # ALTYAPI KATMANI - Tum diger katmanlarin bagimli oldugu temel araclar
│   │   ├── __init__.py
│   │   ├── settings.py           # Pydantic Settings - environment variable yonetimi
│   │   ├── logger.py             # CemilLogger - renkli terminal + dosya loglama
│   │   ├── exceptions.py         # Ozel hata siniflari (CemilBotError, DatabaseError, vb.)
│   │   ├── singleton.py          # SingletonMeta - thread-safe singleton pattern
│   │   ├── rate_limiter.py       # RateLimiter - kullanici bazli istek sinirlandirma
│   │   ├── transaction.py        # Transaction context manager - DB islemleri icin
│   │   └── validators.py         # Pydantic input validation modelleri (PollRequest, FeedbackRequest, vb.)
│   │
│   ├── clients/                  # DIS SERVIS BAGLANTILARI - Uygulamanin disariya acilan noktalari
│   │   ├── __init__.py
│   │   ├── database_client.py    # SQLite baglanti yonetimi, tablo olusturma, migration
│   │   ├── groq_client.py        # Groq LLM API istemcisi (async, model fallback)
│   │   ├── vector_client.py      # FAISS vektor arama istemcisi (embedding + search)
│   │   ├── cron_client.py        # APScheduler zamanlayici yonetimi
│   │   └── smpt_client.py        # SMTP e-posta gonderim istemcisi (Gmail)
│   │
│   ├── commands/                 # SLACK API WRAPPER'LARI - Slack SDK cagrilarini saran yardimci siniflar
│   │   ├── __init__.py
│   │   ├── chat_commands.py      # ChatManager - mesaj gonderme, guncelleme, silme
│   │   ├── conversation_commands.py # ConversationManager - kanal olusturma, arsivleme
│   │   ├── user_commands.py      # UserManager - kullanici bilgisi sorgulama
│   │   ├── canvas_commands.py    # CanvasManager - zengin mesaj bloklari
│   │   ├── pin_commands.py       # PinManager - mesaj sabitleme
│   │   ├── search_commands.py    # SearchManager - mesaj arama
│   │   └── file_commands.py      # FileManager - dosya yukleme/indirme
│   │
│   ├── repositories/             # VERITABANI ERISIM KATMANI - CRUD islemleri
│   │   ├── __init__.py
│   │   ├── base_repository.py    # BaseRepository - tum repository'lerin miras aldigi temel sinif
│   │   ├── user_repository.py    # UserRepository - kullanici CRUD + CSV import
│   │   ├── feedback_repository.py # FeedbackRepository - geri bildirim kayitlari
│   │   ├── match_repository.py   # MatchRepository - kahve eslesmesi kayitlari
│   │   ├── poll_repository.py    # PollRepository - oylama kayitlari
│   │   ├── vote_repository.py    # VoteRepository - bireysel oy kayitlari
│   │   ├── help_repository.py    # HelpRepository - yardim istegi kayitlari
│   │   └── challenge_*.py        # Challenge ile ilgili 7 ayri repository
│   │
│   ├── services/                 # IS MANTIGI KATMANI - Tum business logic burada
│   │   ├── __init__.py
│   │   ├── feedback_service.py   # FeedbackService - geri bildirim toplama ve yonlendirme
│   │   ├── match_service.py      # CoffeeMatchService - kahve eslesmesi algoritmasi
│   │   ├── voting_service.py     # VotingService - oylama olusturma ve yonetimi
│   │   ├── knowledge_service.py  # KnowledgeService - RAG tabanli soru-cevap
│   │   ├── help_service.py       # HelpService - yardim kanali yonetimi
│   │   ├── statistics_service.py # StatisticsService - istatistik raporlama
│   │   └── challenge_*.py        # Challenge ile ilgili 3 ayri service
│   │
│   └── handlers/                 # SLASH KOMUT YONETICILERI - Slack event'lerini dinler
│       ├── __init__.py
│       ├── feedback_handler.py   # /geri-bildirim komutu
│       ├── coffee_handler.py     # /kahve komutu
│       ├── poll_handler.py       # /oylama komutu
│       ├── knowledge_handler.py  # /sor komutu
│       ├── profile_handler.py    # /kayit ve /profilim komutlari
│       ├── health_handler.py     # /cemil-health komutu
│       ├── help_handler.py       # /yardim-iste komutu
│       ├── daily_handler.py      # /daily komutu
│       ├── statistics_handler.py # /admin-istatistik komutu
│       └── challenge_*.py        # Challenge ile ilgili 2 ayri handler
│
├── migrations/                   # SQL migration dosyalari
│   ├── 001_add_canvas_fields.sql
│   ├── 002_remove_canvas_id.sql
│   └── 003_add_jury_status.sql
│
├── tests/                        # Test dosyalari
│   ├── conftest.py               # Pytest fixture'lari (temp_db, mock_env_vars)
│   ├── test_validators.py        # Input validation testleri
│   └── test_rate_limiter.py      # Rate limiter testleri
│
├── scripts/                      # Yardimci betikler
│   └── manage_challenges.py      # Challenge yonetim CLI araci
│
├── .env.example                  # Environment variable sablonu
├── requirements.txt              # Python bagimliliklari
├── deploy.sh                     # Production deployment betiegi
├── start.sh                      # Hizli baslatma betigi
├── pytest.ini                    # Test yapilandirmasi
├── CHANGELOG.md                  # Degisiklik gecmisi
└── CONTRIBUTING.md               # Katkida bulunma rehberi
```

### Katmanlar Arasi Iliski (Yukari → Asagi)

```
  HANDLER  (Slack event'i alir, ack() yapar, service'e iletir)
     │
     ▼
  SERVICE  (Is mantigi: validasyon, orchestration, karar verme)
     │
     ├──► REPOSITORY  (Veritabanina veri yazar/okur)
     │
     ├──► COMMAND MANAGER  (Slack'e mesaj gonderir, kanal acar)
     │
     └──► CLIENT  (Groq, FAISS, Cron gibi dis servisleri cagrir)
```

**KURAL:** Bir ust katman sadece altindaki katmanla konusur. Handler dogrudan repository'ye erismez; service katmani uzerinden erisir. Bu kural, kodun test edilebilir ve bakimi kolay olmasini saglar.

---

## 4. Katman Detaylari

### 4.1 `src/core/` - Altyapi Katmani

Bu klasor, tum diger katmanlarin **ortak olarak bagimli oldugu** temel araclari icerir. Hicbir is mantigi barindirmaz.

#### `settings.py` - Konfigurasyon Yonetimi
- **Teknoloji:** Pydantic Settings (`pydantic-settings`)
- **Ne yapar:** `.env` dosyasindaki degerleri Python nesnelerine cevirir ve dogrular
- **Bagimliliklari:** `.env` dosyasi, `pydantic-settings` paketi
- **Ciktisi:** `BotSettings` nesnesi (tip-guvenli konfigurasyon)
- **Kullanim:**
  ```python
  from src.core.settings import get_settings
  settings = get_settings()
  print(settings.slack_bot_token)  # str, bos birakilamaz
  print(settings.log_level)        # "INFO" (default)
  ```
- **Onemli:** Yeni bir environment variable eklerken bu dosyaya `Field` olarak tanimla.

#### `logger.py` - Loglama Sistemi
- **Teknoloji:** Python `logging` modulu + `RotatingFileHandler`
- **Ne yapar:** Renkli terminal ciktisi + dosyaya yazan loglama sistemi
- **Ciktisi:** Terminal'de renkli loglar + `logs/cemil_detailed.log` dosyasi (max 10MB, 10 yedek)
- **Kullanim:**
  ```python
  from src.core.logger import logger
  logger.info("[>] Islem baslatiliyor...")    # [i] INFO    | ...
  logger.info("[+] Basarili!")                 # [+] INFO    | ...
  logger.warning("[!] Dikkat!")                # [!] WARNING | ...
  logger.error("[X] Hata!", exc_info=True)    # [X] ERROR   | ... (traceback ile)
  ```
- **Log ikonlari konvansiyonu:**
  - `[>]` = Islem basladi
  - `[+]` = Basari
  - `[i]` = Bilgi
  - `[!]` = Uyari
  - `[X]` = Hata

#### `exceptions.py` - Ozel Hata Siniflari
- **Ne yapar:** Projeye ozel exception siniflarini tanimlar
- **Hiyerarsi:**
  ```
  CemilBotError (temel)
  ├── DatabaseError
  ├── SlackClientError
  ├── GroqClientError
  ├── UserRegistrationError
  ├── VotingError
  ├── CoffeeMatchError
  ├── SMTPClientError
  └── PermissionDeniedError
  ```
- **Kural:** Yeni bir ozellik icin ozel hata sinifi gerekirse, `CemilBotError`'dan miras al.

#### `singleton.py` - Singleton Meta Sinifi
- **Ne yapar:** Bir siniftan sadece **tek bir instance** olusturulmasini garanti eder (thread-safe)
- **Kullanildigi yerler:** Tum client'lar (DatabaseClient, GroqClient, VectorClient, CronClient, SMTPClient)
- **Nasil calisir:** Double-checked locking ile `threading.Lock` kullanir
- **Kullanim:**
  ```python
  from src.core.singleton import SingletonMeta

  class MyClient(metaclass=SingletonMeta):
      def __init__(self):
          # Bu __init__ sadece BIR KERE calisir
          self.connection = create_connection()
  ```

#### `rate_limiter.py` - Istek Sinirlandirma
- **Ne yapar:** Kullanici bazinda dakikada max istek sayisini kontrol eder
- **Default:** 10 istek / 60 saniye (settings'ten okunur)
- **Kullanim:**
  ```python
  from src.core.rate_limiter import get_rate_limiter
  rate_limiter = get_rate_limiter(max_requests=10, window_seconds=60)

  allowed, error_msg = rate_limiter.is_allowed(user_id)
  if not allowed:
      # Kullaniciya error_msg goster
      return
  ```

#### `transaction.py` - Veritabani Transaction Yonetimi
- **Ne yapar:** `with` blogu icerisinde otomatik commit/rollback saglar
- **Kullanim:**
  ```python
  from src.core.transaction import transaction

  with transaction(db_client) as conn:
      cursor = conn.cursor()
      cursor.execute("INSERT INTO ...")
      # Basarili olursa otomatik COMMIT
      # Hata olursa otomatik ROLLBACK
  ```

#### `validators.py` - Input Validation Modelleri
- **Teknoloji:** Pydantic `BaseModel`
- **Ne yapar:** Slash komutlarindan gelen kullanici girdisini dogrular ve temizler
- **Mevcut modeller:** `PollRequest`, `FeedbackRequest`, `QuestionRequest`, `HelpRequest`, `ChallengeStartRequest`, `ChallengeJoinRequest`
- **Pattern:** Her model bir `parse_from_text(text: str)` classmethod'una sahiptir
- **Kullanim:**
  ```python
  from src.core.validators import FeedbackRequest

  try:
      request = FeedbackRequest.parse_from_text(user_input)
  except ValueError as e:
      # Hatali input, kullaniciya hata mesaji gonder
      chat_manager.post_ephemeral(..., text=str(e))
      return
  ```
- **Kural:** Yeni bir slash komutu icin mutlaka bir Pydantic validator modeli olustur.

---

### 4.2 `src/clients/` - Dis Servis Baglantilari

Bu klasor, uygulamanin **disariya bagli oldugu servislere** (veritabani, LLM API, vektor DB, e-posta, zamanlayici) baglanmasini saglar. Her client **Singleton** pattern kullanir.

#### `database_client.py` - SQLite Veritabani
- **Teknoloji:** Python `sqlite3` (built-in)
- **Ne yapar:** Veritabani baglantisi yonetimi, tablo olusturma, migration
- **Bagimliliklari:** `SingletonMeta`, dosya sistemi (SQLite dosyasi)
- **Ciktisi:** SQLite connection nesnesi (`sqlite3.Row` formatinda - dict gibi erisilebilir)
- **Onemli methodlar:**
  - `get_connection()` → Yeni bir SQLite baglantisi dondurur
  - `init_db()` → Tum tablolari olusturur (yoksa)
  - `clean_challenge_tables()` → Challenge verilerini siler
- **Yeni tablo eklemek icin:** `init_db()` icine `CREATE TABLE IF NOT EXISTS` ifadesi ekle

#### `groq_client.py` - LLM API Istemcisi
- **Teknoloji:** `groq` paketi (AsyncGroq)
- **Ne yapar:** Groq API uzerinden LLM cagrilari yapar
- **Model fallback mekanizmasi:**
  1. `llama-3.3-70b-versatile` (birincil - yuksek zeka)
  2. `llama-3.1-8b-instant` (yedek 1 - hizli)
  3. `mixtral-8x7b-32768` (yedek 2 - dengeli)
- **Rate limit oldugunda** otomatik olarak sonraki modele gecer
- **Onemli methodlar:**
  - `async chat_completion(messages, model, temp, max_tokens)` → Genel chat tamamlama
  - `async quick_ask(system_prompt, user_prompt)` → Hizli tek soru-cevap

#### `vector_client.py` - Vektor Arama Istemcisi
- **Teknoloji:** FAISS (faiss-cpu) + SentenceTransformers (all-MiniLM-L6-v2)
- **Ne yapar:** Metin parcalarini vektore cevirir ve benzerlik aramasi yapar
- **Arama stratejisi:**
  1. Siki esik (threshold=0.8) ile dene
  2. Az sonuc varsa gevsek esik (1.6) ile tekrar dene
  3. Hala yoksa tum sonuclari dondur
- **Onemli methodlar:**
  - `add_texts(texts, metadata)` → Metin parcalarini indeksle
  - `search(query, top_k, threshold)` → Benzerlik aramasi yap
  - `save_index()` / `load_index()` → Indeksi dosyaya kaydet/yukle

#### `cron_client.py` - Zamanlayici Istemcisi
- **Teknoloji:** APScheduler (`BackgroundScheduler`)
- **Ne yapar:** Periyodik gorevleri (cron job) yonetir
- **Onemli methodlar:**
  - `add_cron_job(func, cron_expr, job_id)` → Tekrarlayan gorev ekle
  - `add_once_job(func, run_date, delay_mins)` → Tek seferlik gorev ekle
  - `remove_job(job_id)` → Gorevi kaldir

#### `smpt_client.py` - E-posta Istemcisi
- **Teknoloji:** Python `smtplib` + `email.mime` (built-in)
- **Ne yapar:** Gmail SMTP uzerinden e-posta gonderir
- **Bagimliliklari:** `SMTP_EMAIL` ve `SMTP_PASSWORD` environment variable'lari

---

### 4.3 `src/commands/` - Slack API Wrapper'lari

Bu klasor, **Slack SDK cagrilarini saran** yardimci siniflar icerir. Handler'lar ve service'ler bu siniflar uzerinden Slack ile iletisim kurar.

> **ONEMLI:** Bu klasordeki "commands" isimlendirmesi yaniltici olabilir. Bunlar slash command degil, Slack API **method wrapper'laridir.** Slash command mantigi `handlers/` klasorundedir.

#### `chat_commands.py` → `ChatManager`
- **Gorevi:** Mesaj gonderme, guncelleme, silme islemleri
- **En cok kullanilan methodlar:**
  - `post_message(channel, text, blocks)` → Kanala mesaj gonder
  - `post_ephemeral(channel, user, text)` → Sadece kullaniciya gorunen gizli mesaj
  - `update_message(channel, ts, text, blocks)` → Mesaj guncelle
  - `delete_message(channel, ts)` → Mesaj sil
- **Ozel davranis:** `post_ephemeral` basarisiz olursa otomatik olarak DM'e doner (fallback)

#### `conversation_commands.py` → `ConversationManager`
- **Gorevi:** Kanal olusturma, arsivleme, uye ekleme/cikarma
- **Onemli:** Kanal olusturma icin `user_token` gereklidir (bot token yetmez)

#### `user_commands.py` → `UserManager`
- **Gorevi:** Slack kullanici bilgisi sorgulama (isim, e-posta)

#### Diger: `CanvasManager`, `PinManager`, `SearchManager`, `FileManager`
- Daha az kullanilan Slack API islemleri

---

### 4.4 `src/repositories/` - Veritabani Erisim Katmani

Bu klasor, **veritabanina veri yazan ve okuyan** siniflari icerir. Her repository bir tabloya karsilik gelir.

#### `base_repository.py` → `BaseRepository` (Temel Sinif)
- **Tum repository'lerin miras aldigi sinif**
- **Hazir CRUD methodlari:**
  - `create(data: Dict) → str` → Yeni kayit olustur (UUID otomatik)
  - `get(record_id: str) → Optional[Dict]` → ID ile kayit getir
  - `update(record_id: str, data: Dict) → bool` → Kayit guncelle (`updated_at` otomatik)
  - `delete(record_id: str) → bool` → Kayit sil
  - `list(filters: Optional[Dict]) → List[Dict]` → Kayitlari listele (filtreleme destekli)
- **Kullanim ornegi:**
  ```python
  class FeedbackRepository(BaseRepository):
      def __init__(self, db_client: DatabaseClient):
          super().__init__(db_client, "feedbacks")  # "feedbacks" = tablo adi

      # BaseRepository'den gelen create, get, update, delete, list hazir!
      # Gerekirse ozel methodlar eklenebilir:

      def get_by_category(self, category: str):
          return self.list(filters={"category": category})
  ```

#### Mevcut Repository'ler

| Repository | Tablo | Amac |
|-----------|-------|------|
| `UserRepository` | `users` | Kullanici profilleri, CSV import |
| `MatchRepository` | `matches` | Kahve eslesmesi kayitlari |
| `PollRepository` | `polls` | Oylama meta verileri |
| `VoteRepository` | `votes` | Bireysel oy kayitlari |
| `FeedbackRepository` | `feedbacks` | Anonim geri bildirimler |
| `HelpRepository` | `help_requests` | Yardim istegi kayitlari |
| `ChallengeHubRepository` | `challenge_hubs` | Challenge meta verileri |
| `ChallengeParticipantRepository` | `challenge_participants` | Takim uyelikleri |
| `ChallengeProjectRepository` | `challenge_projects` | Proje katalogu |
| `ChallengeSubmissionRepository` | `challenge_submissions` | Tamamlanan projeler |
| `ChallengeThemeRepository` | `challenge_themes` | Challenge kategorileri |
| `UserChallengeStatsRepository` | `user_challenge_stats` | Performans istatistikleri |
| `ChallengeEvaluationRepository` | `challenge_evaluations` | Degerlendirme oylari |
| `ChallengeEvaluatorRepository` | `challenge_evaluators` | Degerlendirici atamalari |

---

### 4.5 `src/services/` - Is Mantigi Katmani

Bu klasor, **tum business logic'in** yazildigi katmandir. Service'ler handler'lardan cagirilir ve repository'ler, command manager'lar ve client'lar ile iletisim kurar.

**Bir service sinifi su bilesenlere bagimlidir (Dependency Injection ile alinir):**
- `ChatManager` → Slack'e mesaj gonder
- `Repository` → Veritabaninda CRUD
- `Client` → Dis servisleri cagir (Groq, FAISS, Cron, SMTP)

#### Ornek: `FeedbackService` (En basit service)

```python
class FeedbackService:
    """Anonim geri bildirimleri yoneten servis."""

    def __init__(self, chat_manager, smtp_client, feedback_repo):
        self.chat = chat_manager          # Slack mesaj gonderme
        self.smtp = smtp_client           # E-posta gonderme
        self.repo = feedback_repo         # Veritabani erisimi

    async def submit_feedback(self, content: str, category: str = "general"):
        # 1. Veritabanina kaydet
        feedback_id = self.repo.create({"content": content, "category": category})

        # 2. Admin kanalina bildir (Slack)
        self.chat.post_message(channel=admin_channel, text=...)

        # 3. E-posta ile bildir
        self.smtp.send_email(to_emails=..., subject=..., body=...)
```

**Kural:** Service methodlari `async` olabilir (Groq API cagiriyorsa). Handler'dan `asyncio.run()` ile cagrilir.

---

### 4.6 `src/handlers/` - Slash Komut Yoneticileri

Bu klasor, Slack'ten gelen **slash komutlarini ve event'leri dinleyen** fonksiyonlari icerir. Her handler dosyasi bir `setup_*_handlers()` fonksiyonu export eder.

#### Handler Yapisi (Pattern)

```python
"""
Handler'in ne yaptigi aciklamasi.
"""

import asyncio
from slack_bolt import App
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.core.validators import MyValidator       # Input validation modeli
from src.commands import ChatManager
from src.services import MyService
from src.repositories import UserRepository


def setup_my_handlers(
    app: App,
    my_service: MyService,
    chat_manager: ChatManager,
    user_repo: UserRepository
):
    """Handler'lari Slack App'e kaydeder."""
    settings = get_settings()
    rate_limiter = get_rate_limiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window
    )

    @app.command("/my-command")
    def handle_my_command(ack, body):
        """Komutun ne yaptigi."""
        # 1. HEMEN ack() cagir (Slack 3 saniye bekler)
        ack()

        # 2. Temel bilgileri al
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        text = body.get("text", "").strip()

        # 3. Rate limiting kontrolu
        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        # 4. Kullanici bilgisini al (loglama icin)
        try:
            user_data = user_repo.get_by_slack_id(user_id)
            user_name = user_data.get('full_name', user_id) if user_data else user_id
        except Exception:
            user_name = user_id

        # 5. Log kaydi
        logger.info(f"[>] /my-command komutu geldi | Kullanici: {user_name} ({user_id})")

        # 6. Input validation
        if not text:
            chat_manager.post_ephemeral(
                channel=channel_id, user=user_id,
                text="Kullanim: /my-command <parametre>"
            )
            return

        try:
            request = MyValidator.parse_from_text(text)
        except ValueError as e:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=str(e))
            return

        # 7. Async is mantigi
        async def process():
            try:
                await my_service.do_something(request.param)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Basarili!"
                )
                logger.info(f"[+] /my-command tamamlandi | Kullanici: {user_name}")
            except Exception as e:
                logger.error(f"[X] /my-command hatasi: {e}", exc_info=True)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Bir hata olustu. Lutfen tekrar deneyin."
                )

        asyncio.run(process())
```

**Handler'larin gorevi SADECE sudur:**
1. `ack()` cagirmak (Slack'e "aldim" demek)
2. Kullanici girdisini almak ve dogrulamak
3. Rate limiting kontrolu yapmak
4. Service'e yonlendirmek
5. Sonucu kullaniciya iletmek

**Handler'da OLMAMASI gerekenler:**
- Veritabani sorgusu (repository'nin isi)
- Is mantigi hesaplamasi (service'in isi)
- Dis servis cagrisi (client'in isi)

---

## 5. Veri Akisi (Data Flow)

Bir slash komutunun basindan sonuna kadar nasil calistigini gormek icin `/geri-bildirim` ornegini inceleyelim:

```
Kullanici Slack'te yazar: /geri-bildirim genel Harika bir topluluk!
    │
    ▼
[1] SLACK → feedback_handler.py → handle_feedback_command(ack, body)
    │   ack() cagirilir (Slack'e 3 saniye icinde "aldim" der)
    │
    ▼
[2] HANDLER: Rate limit kontrolu
    │   rate_limiter.is_allowed(user_id) → (True, None)
    │
    ▼
[3] HANDLER: Input validation
    │   FeedbackRequest.parse_from_text("genel Harika bir topluluk!")
    │   → FeedbackRequest(category="genel", content="Harika bir topluluk!")
    │
    ▼
[4] HANDLER → SERVICE: feedback_service.submit_feedback(content, category)
    │
    ▼
[5] SERVICE: Veritabanina kaydet
    │   feedback_repo.create({"content": ..., "category": ...})
    │   → BaseRepository.create() → INSERT INTO feedbacks → UUID doner
    │
    ▼
[6] SERVICE: Admin kanalina bildir
    │   chat_manager.post_message(channel=admin_channel, text=...)
    │   → ChatManager → Slack API → chat.postMessage
    │
    ▼
[7] SERVICE: E-posta gonder
    │   smtp_client.send_email(to=admin_email, subject=..., body=...)
    │   → SMTPClient → Gmail SMTP → e-posta gonderildi
    │
    ▼
[8] HANDLER: Kullaniciya onay mesaji
    │   chat_manager.post_ephemeral(text="Geri bildiriminiz iletildi!")
    │
    ▼
[9] LOG: "[+] GERI BILDIRIM ALINDI | Kullanici: Fatih (U123) | Kategori: genel"
```

---

## 6. Yeni Ozellik Ekleme Rehberi (Adim Adim)

Diyelim ki `/motivasyon` adinda yeni bir slash komutu eklemek istiyorsun. Bu komut veritabanina kaydedilecek ve kullaniciya bir motivasyon mesaji donecek. Isik sirasi:

### Adim 1: Veritabani Tablosu Olustur

**Dosya:** `src/clients/database_client.py` icindeki `init_db()` methoduna ekle:

```sql
CREATE TABLE IF NOT EXISTS motivations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

### Adim 2: Migration Dosyasi Olustur (Varolan DB icin)

**Dosya:** `migrations/004_add_motivations_table.sql`

```sql
-- Motivasyon tablosu ekleme (v1.X.X)
CREATE TABLE IF NOT EXISTS motivations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

### Adim 3: Validator Olustur

**Dosya:** `src/core/validators.py` icine ekle:

```python
class MotivationRequest(BaseModel):
    """Motivasyon komutu icin input validation."""

    message: str = Field(..., description="Motivasyon mesaji")

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Mesaj bos olamaz')
        if len(v) > 500:
            raise ValueError('Mesaj en fazla 500 karakter olabilir')
        return v

    @classmethod
    def parse_from_text(cls, text: str) -> 'MotivationRequest':
        if not text:
            raise ValueError("Motivasyon mesaji gerekli")
        return cls(message=text)
```

### Adim 4: Repository Olustur

**Dosya:** `src/repositories/motivation_repository.py`

```python
from src.repositories.base_repository import BaseRepository
from src.clients.database_client import DatabaseClient

class MotivationRepository(BaseRepository):
    """Motivasyon kayitlari icin veritabani erisim sinifi."""

    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "motivations")

    # Ozel sorgular gerekirse ekle:
    def get_by_user(self, user_id: str):
        return self.list(filters={"user_id": user_id})
```

### Adim 5: Service Olustur

**Dosya:** `src/services/motivation_service.py`

```python
from src.core.logger import logger
from src.commands import ChatManager
from src.clients import GroqClient
from src.repositories.motivation_repository import MotivationRepository

class MotivationService:
    """Motivasyon mesajlari ureten ve kaydeden servis."""

    def __init__(self, chat_manager: ChatManager, groq_client: GroqClient, motivation_repo: MotivationRepository):
        self.chat = chat_manager
        self.groq = groq_client
        self.repo = motivation_repo

    async def generate_and_save(self, user_id: str) -> str:
        """Yapay zeka ile motivasyon mesaji uret ve kaydet."""
        # 1. LLM'den motivasyon mesaji al
        message = await self.groq.quick_ask(
            system_prompt="Sen motive edici bir kocsun. Kisa ve etkili Turkce motivasyon mesajlari uret.",
            user_prompt="Bana gunluk bir motivasyon mesaji ver."
        )

        # 2. Veritabanina kaydet
        self.repo.create({"user_id": user_id, "message": message})

        logger.info(f"[+] Motivasyon mesaji uretildi | Kullanici: {user_id}")
        return message
```

### Adim 6: Handler Olustur

**Dosya:** `src/handlers/motivation_handler.py`

```python
"""
Motivasyon slash komut handler'i.
/motivasyon komutu ile yapay zeka tabanli motivasyon mesaji uretir.
"""

import asyncio
from slack_bolt import App
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.commands import ChatManager
from src.services.motivation_service import MotivationService
from src.repositories import UserRepository


def setup_motivation_handlers(
    app: App,
    motivation_service: MotivationService,
    chat_manager: ChatManager,
    user_repo: UserRepository
):
    """Motivasyon handler'larini kaydeder."""
    settings = get_settings()
    rate_limiter = get_rate_limiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window
    )

    @app.command("/motivasyon")
    def handle_motivation_command(ack, body):
        """Yapay zeka ile motivasyon mesaji uretir."""
        ack()

        user_id = body["user_id"]
        channel_id = body["channel_id"]

        # Rate limiting
        allowed, error_msg = rate_limiter.is_allowed(user_id)
        if not allowed:
            chat_manager.post_ephemeral(channel=channel_id, user=user_id, text=error_msg)
            return

        logger.info(f"[>] /motivasyon komutu geldi | Kullanici: {user_id}")

        async def process():
            try:
                message = await motivation_service.generate_and_save(user_id)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text=f"💪 *Gunun Motivasyonu:*\n\n{message}"
                )
                logger.info(f"[+] /motivasyon tamamlandi | Kullanici: {user_id}")
            except Exception as e:
                logger.error(f"[X] /motivasyon hatasi: {e}", exc_info=True)
                chat_manager.post_ephemeral(
                    channel=channel_id, user=user_id,
                    text="Motivasyon mesaji olusturulurken bir hata olustu."
                )

        asyncio.run(process())
```

### Adim 7: `__init__.py` Dosyalarini Guncelle

**Her yeni dosya icin ilgili `__init__.py`'ye import ve `__all__` eklenmeli:**

1. **`src/repositories/__init__.py`** icine ekle:
   ```python
   from .motivation_repository import MotivationRepository
   # __all__ listesine "MotivationRepository" ekle
   ```

2. **`src/services/__init__.py`** icine ekle:
   ```python
   from .motivation_service import MotivationService
   # __all__ listesine "MotivationService" ekle
   ```

3. **`src/handlers/__init__.py`** icine ekle:
   ```python
   from .motivation_handler import setup_motivation_handlers
   # __all__ listesine "setup_motivation_handlers" ekle
   ```

### Adim 8: `bot.py` Icinde Kayit Et

**Dosya:** `src/bot.py` - 4 farkli bolume ekleme yapilir:

```python
# --- (1) Import bolumu ---
from src.repositories import MotivationRepository      # Yeni
from src.services import MotivationService              # Yeni
from src.handlers import setup_motivation_handlers      # Yeni

# --- (2) Repository ilklendirme bolumu ---
motivation_repo = MotivationRepository(db_client)       # Yeni

# --- (3) Service ilklendirme bolumu ---
motivation_service = MotivationService(                 # Yeni
    chat_manager, groq_client, motivation_repo
)

# --- (4) Handler kayit bolumu ---
setup_motivation_handlers(app, motivation_service, chat_manager, user_repo)  # Yeni
```

### Adim 9: Slack Uygulama Panelinde Slash Komutu Tanimla

Slack App Dashboard'a git → Slash Commands → "Create New Command":
- **Command:** `/motivasyon`
- **Short Description:** Yapay zeka ile motivasyon mesaji al
- **Usage Hint:** (bos birakilabilir)

---

## 7. Kodlama Kurallari ve Konvansiyonlar

### Isimlendirme Kurallari

| Ne | Format | Ornek |
|----|--------|-------|
| Dosya adi | `snake_case` | `motivation_handler.py` |
| Sinif adi | `PascalCase` | `MotivationService` |
| Fonksiyon/method | `snake_case` | `generate_and_save()` |
| Degisken | `snake_case` | `user_name` |
| Constant | `UPPER_SNAKE_CASE` | `NON_INTERACTIVE` |
| Handler setup fonksiyonu | `setup_*_handlers` | `setup_motivation_handlers` |
| Slash komut | `/kebab-case` | `/geri-bildirim` |
| Tablo adi (DB) | `snake_case` (cogul) | `motivations` |

### Import Sirasi

```python
# 1. Standart kutuphane
import os
import asyncio

# 2. Ucuncu parti paketler
from slack_bolt import App
from pydantic import BaseModel

# 3. Proje icindeki core modulleri
from src.core.logger import logger
from src.core.settings import get_settings
from src.core.rate_limiter import get_rate_limiter
from src.core.validators import MyValidator

# 4. Proje icindeki diger modulleri
from src.commands import ChatManager
from src.services import MyService
from src.repositories import UserRepository
```

### Docstring Kurallari

```python
class MyService:
    """
    Bir satirlik aciklama.
    """

    def __init__(self, chat_manager: ChatManager, my_repo: MyRepository):
        self.chat = chat_manager
        self.repo = my_repo

    async def do_something(self, param: str) -> str:
        """
        Metodun ne yaptigi (tek satirlik).
        """
        ...
```

### Log Mesaji Formati

```python
# Islem basladinda
logger.info(f"[>] /komut-adi komutu geldi | Kullanici: {user_name} ({user_id}) | Kanal: {channel_id}")

# Basari
logger.info(f"[+] /komut-adi tamamlandi | Kullanici: {user_name} ({user_id}) | Sonuc: {result}")

# Uyari
logger.warning(f"[!] Beklenmedik durum | Detay: {detail}")

# Hata (exc_info=True ile traceback ekle)
logger.error(f"[X] /komut-adi hatasi: {e}", exc_info=True)
```

### Mesaj Gonderme Kurallari

| Durum | Yontem | Neden |
|-------|--------|-------|
| Hata/uyari mesaji | `post_ephemeral` | Sadece kullanici gorsun, kanali kirletmesin |
| Basari/sonuc mesaji | `post_ephemeral` veya `post_message` | Icerige gore karar ver |
| Tum kanala duyuru | `post_message` | Herkes gormeli |
| Admin bildirimi | `post_message(channel=admin_channel)` | Admin kanalina gonder |

### Async Kullanim Kurali

- **Groq API cagrisi varsa** → method `async` olmali
- **Sadece DB islemleri varsa** → sync yeterli
- **Handler'dan async service cagirmak icin:**
  ```python
  async def process():
      await my_service.async_method()
  asyncio.run(process())
  ```

---

## 8. Kayit (Registration) Kontrol Listesi

Yeni ozellik eklerken **tum bu noktalarda** kayit yapildigini kontrol et:

- [ ] `src/clients/database_client.py` → `init_db()` icine yeni tablo (CREATE TABLE)
- [ ] `migrations/` → Yeni migration dosyasi (varolan DB'ler icin)
- [ ] `src/core/validators.py` → Yeni Pydantic validator modeli
- [ ] `src/repositories/` → Yeni repository dosyasi
- [ ] `src/repositories/__init__.py` → Import + `__all__` guncelleme
- [ ] `src/services/` → Yeni service dosyasi
- [ ] `src/services/__init__.py` → Import + `__all__` guncelleme
- [ ] `src/handlers/` → Yeni handler dosyasi
- [ ] `src/handlers/__init__.py` → Import + `__all__` guncelleme
- [ ] `src/bot.py` → 4 bolumde kayit:
  - [ ] Import
  - [ ] Repository ilklendirme
  - [ ] Service ilklendirme
  - [ ] Handler kaydi (`setup_*_handlers(...)`)
- [ ] Slack App Dashboard → Slash command tanimlanmasi
- [ ] `.env.example` → Yeni environment variable varsa eklenmesi
- [ ] `src/core/settings.py` → Yeni setting `Field` olarak eklenmesi
- [ ] `src/core/exceptions.py` → Yeni exception sinifi (gerekirse)

---

## 9. Hata Yonetimi Kurallari

### Genel Pattern

```python
# SERVICE icinde
async def do_something(self, param):
    try:
        # Is mantigi
        result = self.repo.create(...)
        return result
    except Exception as e:
        logger.error(f"[X] MyService.do_something hatasi: {e}", exc_info=True)
        raise  # veya return False/None

# HANDLER icinde
async def process():
    try:
        await my_service.do_something(param)
        chat_manager.post_ephemeral(channel=channel_id, user=user_id, text="Basarili!")
    except Exception as e:
        logger.error(f"[X] /komut hatasi: {e}", exc_info=True)
        chat_manager.post_ephemeral(
            channel=channel_id, user=user_id,
            text="Bir hata olustu. Lutfen tekrar deneyin."
        )
```

### Kurallar

1. **`ack()` her zaman ilk satirda cagrilmali.** Slack 3 saniye icinde yanit bekler.
2. **Kullaniciya teknik hata mesaji gosterme.** Genel bir mesaj yaz, detayi logla.
3. **`exc_info=True` ile logla.** Traceback olmadan hata ayiklamak zordur.
4. **Repository hatalari `DatabaseError` firlatir** (base_repository.py icinde). Service bunlari yakalayabilir.
5. **Global error handler** (`bot.py` icindeki `@app.error`) yakalanmamis tum hatalari loglar.

---

## 10. Test Yazma Rehberi

### Mevcut Yapi

```ini
# pytest.ini
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

### Test Dosyasi Isimlendirme

```
tests/
├── test_validators.py           # src/core/validators.py testleri
├── test_rate_limiter.py         # src/core/rate_limiter.py testleri
└── test_motivation_service.py   # (ornek) yeni service testleri
```

### Test Ornegi

```python
# tests/test_motivation_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestMotivationService:
    def setup_method(self):
        self.chat_manager = MagicMock()
        self.groq_client = MagicMock()
        self.groq_client.quick_ask = AsyncMock(return_value="Harika bir gun!")
        self.motivation_repo = MagicMock()

        self.service = MotivationService(
            self.chat_manager, self.groq_client, self.motivation_repo
        )

    @pytest.mark.asyncio
    async def test_generate_and_save_success(self):
        result = await self.service.generate_and_save("U123")

        assert result == "Harika bir gun!"
        self.motivation_repo.create.assert_called_once()
        self.groq_client.quick_ask.assert_called_once()
```

### Testleri Calistirma

```bash
python -m pytest tests/ -v
```

---

## 11. PR (Pull Request) Kontrol Listesi

PR acmadan once bu listeyi kontrol et:

### Kod Kalitesi
- [ ] Tum yeni fonksiyonlarda docstring var mi?
- [ ] Log mesajlari `[>]`, `[+]`, `[!]`, `[X]` ikonlariyla formatli mi?
- [ ] Import sirasi dogru mu? (standart → ucuncu parti → proje)
- [ ] Isimlendirme kurallarına uyuyor mu? (snake_case, PascalCase)

### Mimari
- [ ] Handler icinde is mantigi yok, sadece yonlendirme mi?
- [ ] Service Dependency Injection ile bagimlilik aliyor mu?
- [ ] Repository `BaseRepository`'den miras aliyor mu?
- [ ] `__init__.py` dosyalari guncellendi mi?
- [ ] `bot.py` icinde 4 bolumde kayit yapildi mi?

### Guvenlik
- [ ] Kullanici girdisi Pydantic validator ile dogrulaniyor mu?
- [ ] Rate limiting uygulanmis mi?
- [ ] Hassas bilgi (token, sifre) loglanmiyor mu?
- [ ] Hata mesajlarinda teknik detay kullaniciya gosterilmiyor mu?

### Test
- [ ] Yeni ozellik icin en az 1 test yazildi mi?
- [ ] Mevcut testler gecmeye devam ediyor mu? (`python -m pytest tests/ -v`)

### Dokumantasyon
- [ ] `.env.example` guncellendi mi? (yeni env var varsa)
- [ ] `CHANGELOG.md` guncellendi mi?
- [ ] Slash komut Slack Dashboard'da tanimlanacak mi? (PR aciklamasinda belirt)

---

> **Bu belge, Cemil Bot projesindeki kodlama kurallarini ve mimariyi yansitir.**
> **Yeni bir ozellik eklerken bu belgeyi referans olarak kullan ve kontrol listelerini takip et.**
