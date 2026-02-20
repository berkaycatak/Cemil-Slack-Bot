# Glossary Feature - Yapilan Degisiklikler

> **Tarih:** 2026-02-19
> **Kapsam:** Topluluk sozlugu, quiz sistemi, gunluk bulten, statik web sayfasi
> **Toplam Yeni/Degistirilmis Dosya:** 23
> **Test Sayisi:** 42 (tumu PASS)

---

## Icindekiler

1. [Genel Bakis](#1-genel-bakis)
2. [Veritabani Degisiklikleri (7 tablo)](#2-veritabani-degisiklikleri)
3. [Validator'lar (Input Validation)](#3-validatorlar)
4. [Repository'ler (7 adet)](#4-repositoryler)
5. [Exception Siniflari](#5-exception-siniflari)
6. [GlossaryService](#6-glossaryservice)
7. [QuizService](#7-quizservice)
8. [Glossary Handler (Slash Komutlari + Butonlar)](#8-glossary-handler)
9. [Quiz Handler](#9-quiz-handler)
10. [bot.py Entegrasyonu](#10-botpy-entegrasyonu)
11. [Statik HTML Uretici](#11-statik-html-uretici)
12. [Settings ve .env Degisiklikleri](#12-settings-ve-env)
13. [Test Altyapisi (conftest.py)](#13-test-altyapisi)
14. [Slack App Konfigurasyonu (Manuel)](#14-slack-app-konfigurasyonu)

---

## 1. Genel Bakis

### Ne eklendi?

| Ozellik | Slash Komutu | Aciklama |
|---------|-------------|----------|
| Terim onerme | `/terim Docker` | AI validasyon + skor bazli otomatik/admin onay |
| Aciklama ekleme | `/acikla Docker \| Konteyner platformu` | Coklu aciklama + faydali tepkisi |
| Terim goruntuleme | `/glossary Docker` | Terim detayi + aciklamalar + faydali butonu |
| Quiz | `/quiz` | AI uretimli 3 soruluk bilgi yarismasi |
| Gunluk bulten | Otomatik (09:00) | 5 tanimsiz + 3 tanimli terim, butonlarla |
| Web sayfasi | `python scripts/generate_glossary_html.py` | Statik HTML arama + filtre |

### Mimari katmanlar (mevcut pattern'e sadik)

```
Handler (glossary_handler.py, quiz_handler.py)
   |
   v
Service (glossary_service.py, quiz_service.py)
   |
   v
Repository (7 adet, hepsi BaseRepository'den turetilmis)
   |
   v
DatabaseClient (SQLite - mevcut)
```

### Dosya listesi

**Yeni dosyalar (15):**
```
src/repositories/glossary_term_repository.py
src/repositories/glossary_definition_repository.py
src/repositories/glossary_reaction_repository.py
src/repositories/daily_term_log_repository.py
src/repositories/daily_term_reaction_repository.py
src/repositories/quiz_session_repository.py
src/repositories/quiz_answer_repository.py
src/services/glossary_service.py
src/services/quiz_service.py
src/handlers/glossary_handler.py
src/handlers/quiz_handler.py
scripts/generate_glossary_html.py
migrations/004_add_glossary_tables.sql
tests/test_glossary_validators.py
tests/test_glossary_repositories.py
tests/test_glossary_service.py
tests/test_quiz_service.py
```

**Degistirilen dosyalar (8):**
```
src/clients/database_client.py        -> 7 CREATE TABLE + 8 index
src/core/validators.py                -> TermRequest + DefinitionRequest
src/core/exceptions.py                -> GlossaryError + QuizError
src/core/settings.py                  -> glossary_daily_channel + threshold
src/repositories/__init__.py          -> 7 yeni repo export
src/services/__init__.py              -> 2 yeni service export
src/handlers/__init__.py              -> 2 yeni handler export
src/bot.py                            -> Tam entegrasyon + cron job
.env.example                          -> 2 yeni env degiskeni
tests/conftest.py                     -> Agir bagimliliklari mock'lama
```

---

## 2. Veritabani Degisiklikleri

### Dosyalar
- `src/clients/database_client.py` (degistirildi - `init_db()` metodu icine eklendi)
- `migrations/004_add_glossary_tables.sql` (yeni - ayni SQL'in standalone versiyonu)

### 7 yeni tablo

#### 2.1 glossary_terms (Terimler)

```sql
CREATE TABLE IF NOT EXISTS glossary_terms (
    id              TEXT PRIMARY KEY,
    term            TEXT NOT NULL UNIQUE,          -- Terim adi (benzersiz)
    category        TEXT NOT NULL,                 -- AI tarafindan atanan kategori
    term_type       TEXT NOT NULL DEFAULT 'term',  -- 'term' veya 'topic'
    related_terms   TEXT,                          -- JSON array: ["SGD", "Adam"]
    ai_score        REAL NOT NULL DEFAULT 0.0,     -- 0.0 - 10.0 arasi AI skoru
    status          TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'approved' | 'rejected'
    submitted_by    TEXT NOT NULL,                 -- Gonderen kullanici (slack_id)
    ai_validation   TEXT,                          -- AI'nin tam JSON yaniti
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

**Durum akisi:**
- `score >= 7.0` → `status = 'approved'` (otomatik onay)
- `score < 7.0` → `status = 'pending'` (admin onay bekler)
- Admin onayla → `'approved'` / Admin reddet → `'rejected'`

#### 2.2 glossary_definitions (Aciklamalar)

```sql
CREATE TABLE IF NOT EXISTS glossary_definitions (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,                 -- Hangi terime ait
    definition      TEXT NOT NULL,                 -- Aciklama metni
    contributor_id  TEXT NOT NULL,                 -- Aciklamayi yazan kullanici
    helpful_count   INTEGER NOT NULL DEFAULT 0,    -- Denormalize faydali sayaci
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
    FOREIGN KEY (contributor_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

**Neden `helpful_count` denormalize?**
Her aciklama gosterildiginde `glossary_reactions` tablosunda COUNT sorgusu calistirmak yerine, burada sakliyoruz. Tepki eklendiginde/kaldirildiginda her iki tablo da guncellenir.

#### 2.3 glossary_reactions (Faydali Tepkileri)

```sql
CREATE TABLE IF NOT EXISTS glossary_reactions (
    id              TEXT PRIMARY KEY,
    definition_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    reaction_type   TEXT NOT NULL DEFAULT 'helpful',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(definition_id, user_id, reaction_type),  -- Kullanici basina tek tepki
    FOREIGN KEY (definition_id) REFERENCES glossary_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

#### 2.4 daily_term_logs (Gunluk Bulten Kayitlari)

```sql
CREATE TABLE IF NOT EXISTS daily_term_logs (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,
    post_type       TEXT NOT NULL,       -- 'undefined' | 'defined'
    message_ts      TEXT,                -- Slack mesaj timestamp (guncelleme icin)
    channel_id      TEXT,
    posted_at       DATE NOT NULL,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
);
```

**Ne ise yarar?** Ayni terimin tekrar gunluk bultende gonderilmesini onler.

#### 2.5 daily_term_reactions (Bulten Tepkileri)

```sql
CREATE TABLE IF NOT EXISTS daily_term_reactions (
    id              TEXT PRIMARY KEY,
    daily_log_id    TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    reaction_type   TEXT NOT NULL,       -- 'knew' | 'didnt_know'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(daily_log_id, user_id),       -- Kullanici basina tek tepki
    FOREIGN KEY (daily_log_id) REFERENCES daily_term_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

#### 2.6 quiz_sessions (Quiz Oturumlari)

```sql
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    category        TEXT NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 3,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    wrong_count     INTEGER NOT NULL DEFAULT 0,
    score           INTEGER NOT NULL DEFAULT 0,     -- Dogru basina +10
    status          TEXT NOT NULL DEFAULT 'in_progress',
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

#### 2.7 quiz_answers (Quiz Cevaplari)

```sql
CREATE TABLE IF NOT EXISTS quiz_answers (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    options         TEXT NOT NULL,        -- JSON array: ["A) ...", "B) ...", ...]
    correct_answer  TEXT NOT NULL,        -- "A", "B", "C" veya "D"
    user_answer     TEXT,                 -- Kullanicinin cevabi (NULL = cevaplanmamis)
    is_correct      BOOLEAN,
    answered_at     TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE
);
```

### Eklenen index'ler (8 adet)

```sql
CREATE INDEX IF NOT EXISTS idx_glossary_terms_status ON glossary_terms(status);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_category ON glossary_terms(category);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_term ON glossary_terms(term);
CREATE INDEX IF NOT EXISTS idx_glossary_definitions_term ON glossary_definitions(term_id);
CREATE INDEX IF NOT EXISTS idx_daily_term_logs_date ON daily_term_logs(posted_at);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_score ON quiz_sessions(score DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_session ON quiz_answers(session_id);
```

### Tablo iliskileri

```
glossary_terms (1) ──┬── (N) glossary_definitions
                     │            │
                     │            └── (N) glossary_reactions
                     │
                     └── (N) daily_term_logs
                                  │
                                  └── (N) daily_term_reactions

quiz_sessions (1) ── (N) quiz_answers

users ── (FK) ── glossary_terms.submitted_by
      ── (FK) ── glossary_definitions.contributor_id
      ── (FK) ── glossary_reactions.user_id
      ── (FK) ── daily_term_reactions.user_id
      ── (FK) ── quiz_sessions.user_id
```

---

## 3. Validator'lar

### Dosya
- `src/core/validators.py` (degistirildi - dosyanin sonuna 2 sinif eklendi)

### Neden validator?
Projede mevcut pattern: Her slash komutu icin bir Pydantic model. Ham Slack text'ini parse eden `parse_from_text()` classmethod'u ile handler katmanindan parsing mantigi izole edilir.

### TermRequest

```python
class TermRequest(BaseModel):
    term: str = Field(..., description="Terim adi")

    @field_validator('term')
    @classmethod
    def validate_term(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Terim adi bos olamaz')
        if len(v) > 200:
            raise ValueError('Terim adi en fazla 200 karakter olabilir')
        return v

    @classmethod
    def parse_from_text(cls, text: str) -> 'TermRequest':
        if not text or not text.strip():
            raise ValueError("Terim adi gerekli. Ornek: /terim Gradient Descent")
        return cls(term=text.strip())
```

**Kullanim ornegi (handler icinde):**
```python
try:
    req = TermRequest.parse_from_text(body["text"])  # "Gradient Descent"
    # req.term == "Gradient Descent"
except ValueError as ve:
    # Kullaniciya hata mesaji gonder
```

### DefinitionRequest

```python
class DefinitionRequest(BaseModel):
    term: str = Field(...)
    definition: str = Field(...)

    @classmethod
    def parse_from_text(cls, text: str) -> 'DefinitionRequest':
        # "Docker | Konteyner platformu" -> term="Docker", definition="Konteyner platformu"
        # "API | Application | Programming" -> term="API", definition="Application | Programming"
        parts = text.split('|', 1)  # Sadece ilk pipe'dan bol
        ...
```

**Onemli detay:** `split('|', 1)` — ilk `|` ayirici, sonraki `|`'ler aciklamanin parcasi. Ornek:
- Input: `API | Application | Programming Interface`
- Sonuc: `term="API"`, `definition="Application | Programming Interface"`

### Testler (11 adet)
Dosya: `tests/test_glossary_validators.py`

```python
class TestTermRequest:
    def test_valid_term(self):             # Normal terim
    def test_empty_term_raises(self):      # Bos string → ValueError
    def test_whitespace_only_raises(self): # Sadece bosluk → ValueError
    def test_too_long_term_raises(self):   # 201 karakter → ValueError
    def test_whitespace_stripped(self):    # "  Docker  " → "Docker"

class TestDefinitionRequest:
    def test_valid_definition(self):            # Normal parse
    def test_missing_separator_raises(self):    # Pipe yok → ValueError
    def test_empty_definition_raises(self):     # "Docker | " → ValueError
    def test_empty_term_raises(self):           # " | aciklama" → ValueError
    def test_definition_with_multiple_pipes(self): # Birden fazla pipe
    def test_too_long_definition_raises(self):     # 2001 karakter → ValueError
```

---

## 4. Repository'ler

### Dosyalar (7 yeni)
```
src/repositories/glossary_term_repository.py
src/repositories/glossary_definition_repository.py
src/repositories/glossary_reaction_repository.py
src/repositories/daily_term_log_repository.py
src/repositories/daily_term_reaction_repository.py
src/repositories/quiz_session_repository.py
src/repositories/quiz_answer_repository.py
```

### Pattern
Her repository `BaseRepository`'den miras alir. `BaseRepository` zaten CRUD (create, get, update, delete, list) saglar. Ozel sorgular icin ek method'lar eklenir.

```python
class GlossaryTermRepository(BaseRepository):
    def __init__(self, db_client: DatabaseClient):
        super().__init__(db_client, "glossary_terms")  # Tablo adi

    # Ozel sorgular:
    def get_by_term(self, term: str):          # Case-insensitive arama
    def get_approved_without_definitions(self): # Aciklanmamis terimler (bulten icin)
    def get_approved_with_definitions(self):    # Aciklanmis terimler (bulten icin)
    def get_categories(self):                   # Kategori listesi
    def get_by_category(self, category: str):   # Kategoriye gore filtre
    def get_all_approved(self):                 # Tum onaylanmis (HTML icin)
```

### Her repository'nin ozel method'lari

| Repository | Ozel Method'lar | Aciklama |
|-----------|----------------|----------|
| `GlossaryTermRepository` | `get_by_term()`, `get_approved_without_definitions()`, `get_approved_with_definitions()`, `get_categories()`, `get_by_category()`, `get_all_approved()` | Terim arama, filtreleme, bulten icin random secim |
| `GlossaryDefinitionRepository` | `get_by_term_id()`, `user_has_contributed()`, `increment_helpful()`, `decrement_helpful()` | Aciklama listeleme, tekrar kontrolu, faydali sayaci |
| `GlossaryReactionRepository` | `toggle_helpful()` | Tepki ekle/kaldir (toggle) — True=eklendi, False=kaldirildi |
| `DailyTermLogRepository` | `get_posted_term_ids()` | Daha once gonderilmis terim ID'leri (tekrar onleme) |
| `DailyTermReactionRepository` | `set_reaction()`, `get_counts()` | Biliyordum/bilmiyordum kaydet, sayilari getir |
| `QuizSessionRepository` | `get_leaderboard()`, `get_user_stats()` | Toplam skor siralama, kullanici istatistikleri |
| `QuizAnswerRepository` | `get_by_session()`, `get_unanswered()` | Oturumdaki sorular, cevaplanmamis ilk soru |

### toggle_helpful() detayi

```python
def toggle_helpful(self, definition_id: str, user_id: str) -> bool:
    # 1. Bu kullanici daha once tepki vermis mi?
    existing = SELECT ... WHERE definition_id=? AND user_id=? AND reaction_type='helpful'

    if existing:
        # 2a. Evet → Tepkiyi kaldir
        DELETE ... WHERE id=existing.id
        return False  # "Kaldirildi"
    else:
        # 2b. Hayir → Tepki ekle
        INSERT INTO glossary_reactions (...)
        return True   # "Eklendi"
```

### Testler (13 adet)
Dosya: `tests/test_glossary_repositories.py`

**Onemli:** Testler gercek SQLite veritabani kullanir (gecici dosya). `SingletonMeta` cache'i her test oncesi temizlenir. FK constraint icin test kullanicilari (`U123`, `U456`, `U789`) eklenir.

```python
@pytest.fixture
def db():
    SingletonMeta._instances.pop(DatabaseClient, None)  # Singleton temizle
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    client = DatabaseClient(db_path=tmp.name)
    # Test kullanicilari ekle (FK icin)
    with client.get_connection() as conn:
        for uid in ("U123", "U456", "U789"):
            cursor.execute("INSERT OR IGNORE INTO users ...")
    yield client
    SingletonMeta._instances.pop(DatabaseClient, None)
    os.unlink(tmp.name)
```

---

## 5. Exception Siniflari

### Dosya
- `src/core/exceptions.py` (degistirildi)

### Eklenen siniflar

```python
class GlossaryError(CemilBotError):
    """Glossary sistemi (terim, aciklama, gunluk bulten) ile ilgili hatalar."""
    pass

class QuizError(CemilBotError):
    """Quiz sistemi (oturum, soru, puanlama) ile ilgili hatalar."""
    pass
```

**Nerede kullanilir?**
- `GlossaryError`: `glossary_service.send_daily_post()` icinde gunluk bulten gonderilemediginde
- `QuizError`: `quiz_service.start_quiz()` icinde soru uretilemediginde

---

## 6. GlossaryService

### Dosya
- `src/services/glossary_service.py` (yeni)

### Sorumluluk
Handler ile repository/API arasindaki is mantigi katmani. AI validasyon, skor hesaplama, admin bildirim, gunluk bulten olusturma islerini yapar.

### Method'lar

#### 6.1 submit_term(term, user_id) → dict

**Akis:**
```
1. Ayni terim var mi? → get_by_term() → varsa {"status": "duplicate"}
2. AI Validasyon → Groq API'ye prompt gonder
3. AI yaniti parse et → JSON: {is_valid, score, category, term_type, related_terms, reason}
4. is_valid == False → {"status": "invalid", "reason": "..."}
5. score >= 7.0 → status="approved" (otomatik onay)
   score < 7.0  → status="pending" (admin onay bekler)
6. Veritabanina kaydet → term_repo.create(...)
7. Pending ise → Admin kanalina onay butonu gonder
8. Sonuc dondur → {"status": "approved|pending", "score": 8.5, ...}
```

**AI Prompt:**
```
Sen bir teknik terim ve konu validasyon asistanisin.
...
SADECE JSON yanit ver:
{"is_valid":bool,"score":float,"term_type":"term|topic","category":"...","related_terms":[...],"reason":"..."}
```

**Ornek AI yaniti:**
```json
{"is_valid": true, "score": 8.5, "term_type": "term", "category": "DevOps", "related_terms": ["Kubernetes", "Container"], "reason": "Gecerli bir konteyner teknolojisi terimi"}
```

#### 6.2 add_definition(term_name, definition, user_id) → dict

**Akis:**
```
1. Terim var mi? → yoksa {"status": "term_not_found"}
2. Bu kullanici zaten aciklama yazmis mi? → {"status": "already_contributed"}
3. Aciklamayi kaydet
4. Terimi gonderen kisiye DM bildirimi
5. {"status": "success"}
```

#### 6.3 get_term_detail(term_name) → dict | None

```python
# Donusu:
{
    "term": {"id": "...", "term": "Docker", "category": "DevOps", ...},
    "definitions": [
        {"id": "...", "definition": "Konteyner platformu", "helpful_count": 5, ...},
        {"id": "...", "definition": "Sanal ortam araci", "helpful_count": 2, ...},
    ]
}
```

#### 6.4 toggle_helpful(definition_id, user_id) → bool

```python
def toggle_helpful(self, definition_id, user_id):
    added = self.reaction_repo.toggle_helpful(definition_id, user_id)
    if added:
        self.definition_repo.increment_helpful(definition_id)   # helpful_count + 1
    else:
        self.definition_repo.decrement_helpful(definition_id)   # helpful_count - 1
    return added  # True=eklendi, False=kaldirildi
```

#### 6.5 handle_admin_action(term_id, action) → bool

```python
action = "approve" → term_repo.update(term_id, {"status": "approved"})
action = "reject"  → term_repo.update(term_id, {"status": "rejected"})
```

#### 6.6 send_daily_post(channel_id)

**Akis:**
```
1. Daha once gonderilmis terim ID'lerini al (tekrar onleme)
2. 5 aciklanmamis terim sec (random, gonderilmemis)
3. 3 aciklanmis terim sec (random, gonderilmemis)
4. Block Kit mesaj olustur (kartlar + butonlar)
5. serbest-kursu kanalina gonder
6. daily_term_logs tablosuna kaydet (hangi terimler gonderildi)
```

**Gunluk bulten mesaj yapisi:**
```
+----------------------------------+
| Gunun Terimleri - 2026-02-19     |  (Header)
+----------------------------------+
| Aciklama Bekleyen Terimler:      |
| /acikla komutu ile ekleyebilirsin|
+----------------------------------+
| Docker (DevOps)     [Bilmiyordum]|  (Her terim icin buton)
| Gradient (ML)       [Bilmiyordum]|
| ...                              |
+----------------------------------+
| Bugun Ogren:                     |
+----------------------------------+
| API (Web)                        |
| > Uygulama programlama arayuzu   |
| [Biliyordum] [Bilmiyordum]       |
| ...                              |
+----------------------------------+
```

### Testler (12 adet)
Dosya: `tests/test_glossary_service.py`

Tum dis bagimliliklar (Groq, Slack, DB) mock'lanir:

```python
class TestSubmitTerm:
    test_duplicate_term_returns_duplicate    # Ayni terim → "duplicate"
    test_invalid_term_returns_invalid        # AI gecersiz → "invalid"
    test_high_score_auto_approves            # Skor 8.5 → "approved"
    test_low_score_goes_pending              # Skor 5.0 → "pending"

class TestAddDefinition:
    test_term_not_found                      # Terim yok → "term_not_found"
    test_already_contributed                 # Zaten eklenmis → "already_contributed"
    test_success                             # Basarili → "success"

class TestToggleHelpful:
    test_toggle_adds_and_increments          # Ekle → increment_helpful cagirilir
    test_toggle_removes_and_decrements       # Kaldir → decrement_helpful cagirilir

class TestAdminAction:
    test_approve                             # Onayla → status="approved"
    test_reject                              # Reddet → status="rejected"
    test_term_not_found                      # Terim yok → False
```

---

## 7. QuizService

### Dosya
- `src/services/quiz_service.py` (yeni)

### Method'lar

#### 7.1 start_quiz(user_id, category) → dict | None

**Akis:**
```
1. Kategorideki terimleri al → 5'ten az ise None dondur
2. Groq API'ye terim listesi gonder → 3 coktan secmeli soru uret
3. quiz_sessions tablosuna yeni oturum olustur
4. quiz_answers tablosuna 3 soruyu kaydet
5. {"session_id": "...", "questions": [...]} dondur
```

**AI Prompt:**
```
Sen bir teknik bilgi yarismasi soru ureticisisin.
Asagidaki teknik terimlerden 3 coktan secmeli soru uret.
Her sorunun 4 secenegi (A, B, C, D) olsun. Sadece 1 dogru cevap.
Sorular Turkce olsun.

SADECE JSON yanit ver:
{"questions": [{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"A","explanation":"..."}]}
```

#### 7.2 answer_question(session_id, user_answer) → dict

**Akis:**
```
1. Cevaplanmamis ilk soruyu bul → get_unanswered()
2. Dogru mu? → user_answer.upper() == correct_answer.upper()
3. Cevabi kaydet → answer_repo.update(...)
4. Session skorunu guncelle:
   - Dogru → correct_count + 1, score + 10
   - Yanlis → wrong_count + 1
5. Sonraki soru var mi?
   - Evet → {"is_correct": true, "completed": false, "next_question": {...}}
   - Hayir → {"is_correct": true, "completed": true, "summary": {...}}
```

**Puanlama:** Dogru = +10, Yanlis = 0, Toplam max = 30

#### 7.3 get_leaderboard(limit=10)

```python
SELECT user_id,
       SUM(score) as total_score,
       SUM(correct_count) as total_correct,
       SUM(wrong_count) as total_wrong,
       COUNT(id) as quiz_count
FROM quiz_sessions WHERE status = 'completed'
GROUP BY user_id
ORDER BY total_score DESC
LIMIT 10
```

### Testler (6 adet)
Dosya: `tests/test_quiz_service.py`

```python
class TestStartQuiz:
    test_not_enough_terms        # 5'ten az terim → None
    test_success                 # Basarili quiz olusturma

class TestAnswerQuestion:
    test_correct_answer          # Dogru cevap → is_correct=True
    test_wrong_answer            # Yanlis cevap → is_correct=False
    test_last_question_completes # Son soru → completed=True

class TestGetLeaderboard:
    test_returns_leaderboard     # Siralama kontrolu
```

---

## 8. Glossary Handler

### Dosya
- `src/handlers/glossary_handler.py` (yeni)

### Fonksiyon imzasi

```python
def setup_glossary_handlers(
    app: App,
    glossary_service: GlossaryService,
    chat_manager: ChatManager,
    user_repo: UserRepository,
):
```

### 8 handler kaydi

| Dekorator | Fonksiyon | Tetikleyici |
|-----------|----------|-------------|
| `@app.command("/terim")` | `handle_term_command` | `/terim Docker` |
| `@app.command("/acikla")` | `handle_definition_command` | `/acikla Docker \| Konteyner` |
| `@app.command("/glossary")` | `handle_glossary_command` | `/glossary Docker` |
| `@app.action("glossary_admin_approve")` | `handle_admin_approve` | Admin onay butonu |
| `@app.action("glossary_admin_reject")` | `handle_admin_reject` | Admin red butonu |
| `@app.action("glossary_helpful")` | `handle_helpful` | Faydali butonu |
| `@app.action("daily_term_knew")` | `handle_daily_knew` | Biliyordum butonu |
| `@app.action("daily_term_didnt_know")` | `handle_daily_didnt_know` | Bilmiyordum butonu |

### Her handler'in ortak pattern'i

```python
@app.command("/terim")
def handle_term_command(ack, body):
    ack()                                          # 1. Slack'e 3 saniye icinde yanit
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    text = body.get("text", "").strip()

    allowed, error_msg = rate_limiter.is_allowed(user_id)  # 2. Rate limit kontrolu
    if not allowed:
        chat_manager.post_ephemeral(...)           # → Hata mesaji (sadece kullaniciya gorunur)
        return

    try:
        req = TermRequest.parse_from_text(text)    # 3. Input validation
    except ValueError as ve:
        chat_manager.post_ephemeral(...)           # → Validation hata mesaji
        return

    async def process():                           # 4. Async is mantigi
        result = await glossary_service.submit_term(req.term, user_id)
        chat_manager.post_ephemeral(...)           # 5. Sonuc mesaji

    asyncio.run(process())                         # 6. Async'i sync'e cevir
```

### /glossary komutunun Block Kit ciktisi

```python
blocks = [
    {"type": "header", "text": "Docker"},
    {"type": "section", "fields": [
        "Kategori: DevOps",
        "Tur: term"
    ]},
    {"type": "section", "text": "Iliskili: Kubernetes, Container"},
    {"type": "divider"},
    # Her aciklama icin:
    {"type": "section",
     "text": "> Konteyner platformu\n— @user123 | 5 faydali",
     "accessory": {"type": "button", "text": "Faydali", "action_id": "glossary_helpful", "value": "def-id"}
    },
]
```

---

## 9. Quiz Handler

### Dosya
- `src/handlers/quiz_handler.py` (yeni)

### 3 handler kaydi

| Dekorator | Fonksiyon | Tetikleyici |
|-----------|----------|-------------|
| `@app.command("/quiz")` | `handle_quiz_command` | `/quiz` → Kategori secimi |
| `@app.action("quiz_select_category")` | `handle_category_select` | Kategori butonu → Quiz baslat |
| `@app.action("quiz_answer")` | `handle_quiz_answer` | A/B/C/D butonu → Cevap isle |

### Quiz akisi (kullanici perspektifi)

```
1. Kullanici: /quiz
   → Bot: Kategori butonlari gosterir [ML] [DevOps] [Web] ...

2. Kullanici: [DevOps] butonuna tiklar
   → Bot: Soru 1/3: Docker nedir?
          [A) Veritabani] [B) Konteyner] [C) Dil] [D) OS]

3. Kullanici: [B) Konteyner] tiklar
   → Bot: Dogru!
          Soru 2/3: Kubernetes ne ise yarar?
          [A) Orkestrasyon] [B) Derleme] [C) Tasarim] [D) Test]

4. ... (3. soru)

5. Son soru cevaplaninca:
   → Bot: Quiz Tamamlandi!
          Dogru: 2 | Yanlis: 1 | Puan: 20
          Tekrar denemek icin /quiz yaz!
```

### Buton value formati

Quiz cevap butonlarinda `value` alani `session_id:answer` formatinda:

```python
# Buton olusturma:
{"value": f"{session_id}:B"}  # "abc123:B"

# Cevap isleme:
value = body["actions"][0]["value"]    # "abc123:B"
session_id, user_answer = value.split(":", 1)  # "abc123", "B"
```

---

## 10. bot.py Entegrasyonu

### Dosya
- `src/bot.py` (degistirildi)

### 4 bolumde degisiklik

#### 10.1 Import'lar (3 blok)

```python
# Repositories
from src.repositories import (
    ...,  # mevcut
    GlossaryTermRepository,
    GlossaryDefinitionRepository,
    GlossaryReactionRepository,
    DailyTermLogRepository,
    DailyTermReactionRepository,
    QuizSessionRepository,
    QuizAnswerRepository,
)

# Services
from src.services import (
    ...,  # mevcut
    GlossaryService,
    QuizService,
)

# Handlers
from src.handlers import (
    ...,  # mevcut
    setup_glossary_handlers,
    setup_quiz_handlers,
)
```

#### 10.2 Repository baslatlari

```python
glossary_term_repo = GlossaryTermRepository(db_client)
glossary_definition_repo = GlossaryDefinitionRepository(db_client)
glossary_reaction_repo = GlossaryReactionRepository(db_client)
daily_term_log_repo = DailyTermLogRepository(db_client)
daily_term_reaction_repo = DailyTermReactionRepository(db_client)
quiz_session_repo = QuizSessionRepository(db_client)
quiz_answer_repo = QuizAnswerRepository(db_client)
```

#### 10.3 Servis baslatlari

```python
glossary_service = GlossaryService(
    chat_manager, groq_client, cron_client,
    glossary_term_repo, glossary_definition_repo, glossary_reaction_repo,
    daily_term_log_repo, daily_term_reaction_repo, user_repo,
)
quiz_service = QuizService(
    groq_client, glossary_term_repo, quiz_session_repo, quiz_answer_repo
)
```

#### 10.4 Handler kayitlari

```python
setup_glossary_handlers(app, glossary_service, chat_manager, user_repo)
setup_quiz_handlers(app, quiz_service, glossary_service, chat_manager, user_repo)
```

#### 10.5 Cron job (gunluk bulten)

```python
def send_glossary_daily_post():
    glossary_channel = os.environ.get("GLOSSARY_DAILY_CHANNEL")
    if glossary_channel:
        glossary_service.send_daily_post(glossary_channel)

cron_client.add_cron_job(
    func=send_glossary_daily_post,
    cron_expression={"hour": "9", "minute": "0"},
    job_id="glossary_daily_post"
)
```

---

## 11. Statik HTML Uretici

### Dosya
- `scripts/generate_glossary_html.py` (yeni)

### Kullanim

```bash
python scripts/generate_glossary_html.py
# Cikti: data/glossary.html
```

### Ne yapar?
1. Veritabanindaki tum onayli terimleri ve aciklamalari ceker
2. Tek bir HTML dosyasi uretir (inline CSS + JS)
3. Arama kutusu + kategori filtresi + responsive tasarim

### HTML sayfasi ozellikleri
- Terim arama (anlik filtreleme)
- Kategori butonlari (ML, DevOps, Web, ...)
- Her terim karti: isim, kategori, iliskili terimler, aciklamalar, faydali sayilari
- Footer: son guncelleme tarihi + toplam terim sayisi
- Sifir dis bagimlilk (tek HTML dosyasi)

---

## 12. Settings ve .env

### Degistirilen dosyalar
- `src/core/settings.py` (2 yeni alan)
- `.env.example` (2 yeni degisken)

### Yeni ayarlar

```python
# src/core/settings.py icinde:
glossary_daily_channel: Optional[str] = Field(None, description="Gunluk glossary bulteni kanali")
glossary_auto_approve_threshold: float = Field(7.0, description="AI skor esigi")
```

```bash
# .env.example icinde:
GLOSSARY_DAILY_CHANNEL=C_SERBEST_KURSU_CHANNEL_ID
GLOSSARY_AUTO_APPROVE_THRESHOLD=7.0
```

### .env dosyasina eklenmesi gerekenler

```bash
# Kendi .env dosyana ekle:
GLOSSARY_DAILY_CHANNEL=C1234567890    # serbest-kursu kanalinin gercek ID'si
GLOSSARY_AUTO_APPROVE_THRESHOLD=7.0    # 7 ve uzeri otomatik onay (degistirilebilir)
```

---

## 13. Test Altyapisi

### Dosya
- `tests/conftest.py` (degistirildi)

### Neden degistirildi?

Repository testleri `from src.clients.database_client import DatabaseClient` import edince, Python `src/clients/__init__.py` dosyasini yukler. Bu dosya `GroqClient`, `CronClient`, `VectorClient` gibi agirliklari import eder — bunlarin bazilari (`sentence_transformers`, `faiss`, `apscheduler`) test ortaminda bulunmayabilir veya keras/TF uyumsuzluk hatasi verir.

### Cozum

`conftest.py`'nin en basina (fixture'lardan once) modulleri mock'la:

```python
import sys
import types
from unittest.mock import MagicMock

_HEAVY_DEPS = [
    "sentence_transformers", "faiss",
    "apscheduler", "apscheduler.schedulers", "apscheduler.schedulers.background",
    "apscheduler.triggers", "apscheduler.triggers.cron", "apscheduler.triggers.interval",
    "langchain_text_splitters", "transformers",
]
for _mod in _HEAVY_DEPS:
    if _mod not in sys.modules:
        mock = MagicMock()
        mock.__spec__ = types.ModuleType(_mod).__dict__.get("__spec__")
        sys.modules[_mod] = mock
```

**Neden `__spec__` gerekli?** `transformers` kutuphanesi icinde `importlib.util.find_spec("faiss")` cagrisi var. Mock objesinin `__spec__` attribute'u olmazsa `ValueError: faiss.__spec__ is not set` hatasi verir.

---

## 14. Slack App Konfigurasyonu (Manuel)

Bu adimlari Slack API web panelinden (api.slack.com) yapmalisin:

### 14.1 Slash komutlari ekle

**Settings → Slash Commands → Create New Command**

| Command | Request URL | Description |
|---------|-----------|-------------|
| `/terim` | (Socket Mode — URL gerekmez) | Yeni teknik terim oner |
| `/acikla` | (Socket Mode) | Mevcut bir terime aciklama ekle |
| `/glossary` | (Socket Mode) | Terim detayini goruntule |
| `/quiz` | (Socket Mode) | Bilgi yarismasi baslat |

### 14.2 Interactivity ac

**Settings → Interactivity & Shortcuts → Toggle ON**

Bu, buton tiklamalarinin (`glossary_admin_approve`, `glossary_helpful`, `quiz_answer` vb.) bota iletilmesi icin gereklidir.

### 14.3 Bot Token Scopes (zaten mevcut olmali)

- `chat:write` — Mesaj gonderme
- `commands` — Slash komutlari
- `im:write` — DM gonderme (aciklama bildirimi icin)

---

## Testleri Calistirma

```bash
# Tum glossary/quiz testleri:
python -m pytest tests/test_glossary_validators.py tests/test_glossary_repositories.py tests/test_glossary_service.py tests/test_quiz_service.py -v

# Sonuc: 42 passed
```

---

## Ozet: Veri Akis Diyagrami

```
Kullanici
  │
  ├── /terim Docker
  │     └── glossary_handler.handle_term_command()
  │           └── glossary_service.submit_term()
  │                 ├── term_repo.get_by_term() → Tekrar kontrolu
  │                 ├── groq.quick_ask() → AI validasyon
  │                 ├── term_repo.create() → DB'ye kaydet
  │                 └── chat.post_message() → Admin bildirim (pending ise)
  │
  ├── /acikla Docker | Konteyner
  │     └── glossary_handler.handle_definition_command()
  │           └── glossary_service.add_definition()
  │                 ├── term_repo.get_by_term() → Terim var mi?
  │                 ├── definition_repo.user_has_contributed() → Tekrar kontrolu
  │                 ├── definition_repo.create() → Aciklamayi kaydet
  │                 └── chat.post_message() → DM bildirim
  │
  ├── /glossary Docker
  │     └── glossary_handler.handle_glossary_command()
  │           └── glossary_service.get_term_detail()
  │                 ├── term_repo.get_by_term()
  │                 └── definition_repo.get_by_term_id()
  │
  ├── /quiz
  │     └── quiz_handler.handle_quiz_command()
  │           └── glossary_service.get_categories() → Kategori butonlari
  │
  ├── [Kategori butonu]
  │     └── quiz_handler.handle_category_select()
  │           └── quiz_service.start_quiz()
  │                 ├── term_repo.get_by_category()
  │                 ├── groq.quick_ask() → 3 soru uret
  │                 ├── session_repo.create()
  │                 └── answer_repo.create() x 3
  │
  └── [A/B/C/D butonu]
        └── quiz_handler.handle_quiz_answer()
              └── quiz_service.answer_question()
                    ├── answer_repo.get_unanswered()
                    ├── answer_repo.update() → Cevabi kaydet
                    └── session_repo.update() → Skoru guncelle

Cron (09:00)
  └── send_glossary_daily_post()
        └── glossary_service.send_daily_post()
              ├── daily_log_repo.get_posted_term_ids()
              ├── term_repo.get_approved_without_definitions()
              ├── term_repo.get_approved_with_definitions()
              ├── chat.post_message() → serbest-kursu kanalina
              └── daily_log_repo.create() x N
```
