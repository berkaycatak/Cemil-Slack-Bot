# Glossary Feature - Design Document

> **Tarih:** 2026-02-18
> **Durum:** Onaylandi
> **Kapsam:** Glossary terim yonetimi, topluluk katkilari, quiz sistemi, gunluk bulten, statik web sayfasi

---

## 1. Ozet

Cemil Bot'a topluluk odakli bir **Glossary (Sozluk)** sistemi eklenmesi. Kullanicilar teknik terimleri ve konulari bota gonderir, AI valide eder, topluluk uyeleri aciklama ekler ve bilgi yarismasi ile ogrenmeyi pekistirir.

### Temel Bilesenleri

1. **Terim Gonderme** (`/terim`) - AI validasyonu + skor bazli otomatik/admin onay
2. **Aciklama Ekleme** (`/acikla`) - Coklu aciklama + "faydali" tepkisi
3. **Terim Goruntuleme** (`/glossary`) - Terim detayi ve aciklamalari
4. **Quiz** (`/quiz`) - AI tarafindan uretilen 3 soruluk bilgi yarismasi
5. **Gunluk Bulten** (cron) - 5 aciklanmamis + 3 aciklanmis terim, buton tepkileri
6. **Statik Web Sayfasi** - Tum terimleri goruntuleme ve arama

---

## 2. Kararlar

| Karar | Secim | Gerekce |
|-------|-------|---------|
| Terim onay akisi | AI skor bazli (7/10+ otomatik, altiysa admin onay) | Dengeli: kalite kontrolu + hiz |
| Aciklama modeli | Coklu aciklama + "faydali" tepkisi | Zengin icerik + topluluk dogrulamasi |
| Kategori belirleme | AI otomatik atar | Kullanicidan ekstra input istemez |
| Web sayfasi | Tek statik HTML dosyasi | Sifir ek bagimlilik |
| Quiz soru uretimi | AI (Groq) tarafindan | Sinirsiz cesitlilik |
| Gunluk gonderi | Tek birlesik mesaj (sabah 09:00) | Kanal kirliligini onler |
| Faydali butonu konumu | /glossary komutu + gunluk bulten | Her iki senaryoyu kapsar |

---

## 3. Veritabani Semasi

### 3.1 glossary_terms

```sql
CREATE TABLE IF NOT EXISTS glossary_terms (
    id              TEXT PRIMARY KEY,
    term            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,
    term_type       TEXT NOT NULL DEFAULT 'term',        -- 'term' | 'topic'
    related_terms   TEXT,                                -- JSON array
    ai_score        REAL NOT NULL DEFAULT 0.0,           -- 0.0 - 10.0
    status          TEXT NOT NULL DEFAULT 'pending',     -- 'pending' | 'approved' | 'rejected'
    submitted_by    TEXT NOT NULL,
    ai_validation   TEXT,                                -- JSON (AI gerekce)
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_status ON glossary_terms(status);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_category ON glossary_terms(category);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_term ON glossary_terms(term);
```

**Durum akisi:**
- `score >= 7.0` → `status = 'approved'` (otomatik)
- `score < 7.0` → `status = 'pending'` (admin onay bekler)
- Admin onayla → `'approved'` / Admin reddet → `'rejected'`

### 3.2 glossary_definitions

```sql
CREATE TABLE IF NOT EXISTS glossary_definitions (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,
    definition      TEXT NOT NULL,
    contributor_id  TEXT NOT NULL,
    helpful_count   INTEGER NOT NULL DEFAULT 0,          -- Denormalize (hiz icin)
    status          TEXT NOT NULL DEFAULT 'active',      -- 'active' | 'hidden'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
    FOREIGN KEY (contributor_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_glossary_definitions_term ON glossary_definitions(term_id);
```

### 3.3 glossary_reactions

```sql
CREATE TABLE IF NOT EXISTS glossary_reactions (
    id              TEXT PRIMARY KEY,
    definition_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    reaction_type   TEXT NOT NULL DEFAULT 'helpful',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(definition_id, user_id, reaction_type),
    FOREIGN KEY (definition_id) REFERENCES glossary_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

### 3.4 daily_term_logs

```sql
CREATE TABLE IF NOT EXISTS daily_term_logs (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,
    post_type       TEXT NOT NULL,                       -- 'undefined' | 'defined'
    message_ts      TEXT,
    channel_id      TEXT,
    posted_at       DATE NOT NULL,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_daily_term_logs_date ON daily_term_logs(posted_at);
```

### 3.5 daily_term_reactions

```sql
CREATE TABLE IF NOT EXISTS daily_term_reactions (
    id              TEXT PRIMARY KEY,
    daily_log_id    TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    reaction_type   TEXT NOT NULL,                       -- 'knew' | 'didnt_know'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(daily_log_id, user_id),
    FOREIGN KEY (daily_log_id) REFERENCES daily_term_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
```

### 3.6 quiz_sessions

```sql
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    category        TEXT NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 3,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    wrong_count     INTEGER NOT NULL DEFAULT 0,
    score           INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress' | 'completed'
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_score ON quiz_sessions(score DESC);
```

### 3.7 quiz_answers

```sql
CREATE TABLE IF NOT EXISTS quiz_answers (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    options         TEXT NOT NULL,                        -- JSON array
    correct_answer  TEXT NOT NULL,
    user_answer     TEXT,
    is_correct      BOOLEAN,
    answered_at     TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_session ON quiz_answers(session_id);
```

### Tablo Iliskileri

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

## 4. Slash Komut Akislari

### 4.1 /terim <terim_adi>

```
Kullanici → /terim Gradient Descent
  → ack() → rate_limit → bos mu kontrolu
  → glossary_service.submit_term(term, user_id)
     → Ayni terim var mi? (UNIQUE kontrolu)
     → AI Validasyon (Groq API) → JSON ciktisi:
       { is_valid, score, term_type, category, related_terms, reason }
     → score >= 7.0 → status='approved', kullaniciya onay mesaji
     → score < 7.0  → status='pending', admin kanalina onay mesaji
     → is_valid=false → kullaniciya "gecerli terim degil" mesaji
```

**AI Prompt:**
```
Sen bir teknik terim ve konu validasyon asistanisin.
Kullanici bir terim veya konu gonderiyor. Gorevlerin:
1. Gecerli bir teknik/akademik terim veya konu mu?
2. Gecerlilik skoru (0-10, 7+ = kesinlikle gecerli)
3. Terim mi, konu mu?
4. Kategori
5. Iliskili terimler

SADECE JSON yanit ver:
{"is_valid":bool,"score":float,"term_type":"term|topic","category":"...","related_terms":[...],"reason":"..."}
```

### 4.2 /acikla <terim> | <aciklama>

```
Kullanici → /acikla Gradient Descent | Bir fonksiyonun minimumunu...
  → ack() → rate_limit → parse (terim | aciklama)
  → glossary_service.add_definition(term_name, definition, user_id)
     → Terim var mi? (glossary_repo.get_by_term)
     → Bu kullanici zaten aciklama eklmis mi?
     → Aciklamayi kaydet (definition_repo.create)
     → Kullaniciya onay, terimi gonderen kisiye DM bildirimi
```

### 4.3 /glossary <terim_adi>

```
Kullanici → /glossary Gradient Descent
  → ack() → rate_limit
  → glossary_service.get_term_detail(term_name)
     → Terim + tum aciklamalari + helpful sayilari
     → Slack Block Kit ile goster (her aciklama altinda [Faydali] butonu)
```

### 4.4 /quiz

```
Kullanici → /quiz
  → ack() → rate_limit
  → quiz_service.get_categories() → mevcut kategorileri cek
  → Slack butonlari ile kategori secimi sun
  → Kullanici kategori secer (action handler)
  → quiz_service.start_quiz(user_id, category)
     → Kategoriden terimler cek (min 10 terim)
     → Groq API ile 3 coktan secmeli soru uret
     → quiz_sessions + quiz_answers tablolarina kaydet
     → Ilk soruyu goster (A/B/C/D butonlari)
  → Kullanici cevaplar (action handler, her soru icin)
  → 3. soru sonrasi → sonuc karti + puan tablosu
```

**Puanlama:** Dogru = +10, Yanlis = 0, Toplam max = 30

---

## 5. Buton Etkilesimleri (Action Handlers)

| action_id | Nerede | Ne Yapar |
|-----------|--------|----------|
| `glossary_admin_approve` | Admin kanalindaki onay mesaji | Terimi onayla, status='approved' |
| `glossary_admin_reject` | Admin kanalindaki onay mesaji | Terimi reddet, status='rejected' |
| `glossary_helpful` | /glossary komutu + gunluk bulten | Aciklamaya faydali tepkisi (toggle) |
| `daily_term_knew` | Gunluk bulten | "Biliyordum" tepkisi |
| `daily_term_didnt_know` | Gunluk bulten | "Bilmiyordum" tepkisi |
| `quiz_select_category` | /quiz sonrasi kategori secimi | Quiz baslatma |
| `quiz_answer` | Quiz sorusu altindaki A/B/C/D | Soruya cevap verme |

---

## 6. Gunluk Cron Job (09:00)

```
glossary_service.send_daily_post()
  → 5 aciklanmamis terim sec (daha once gonderilmemis, random)
  → 3 aciklanmis terim sec (daha once "defined" olarak gonderilmemis, random)
  → Tek birlesik mesaj olarak serbest-kursu kanalina gonder
  → daily_term_logs tablosuna kaydet (message_ts ile)
```

---

## 7. Statik Web Sayfasi

- **Teknoloji:** Tek HTML dosyasi (inline CSS + JS)
- **Uretim:** `scripts/generate_glossary_html.py` veya `glossary_service.generate_html()`
- **Konum:** `data/glossary.html`
- **Ozellikler:** Terim arama, kategori filtresi, katki tablosu, responsive
- **Hosting:** GitHub Pages veya basit HTTP server

---

## 8. Dosya Yapisi

### Yeni Dosyalar (12)

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
```

### Degistirilecek Dosyalar (7)

```
src/clients/database_client.py      → init_db() icine 7 yeni CREATE TABLE
src/core/validators.py              → TermRequest, DefinitionRequest modelleri
src/core/exceptions.py              → GlossaryError, QuizError (opsiyonel)
src/repositories/__init__.py        → 7 yeni repository import + __all__
src/services/__init__.py            → 2 yeni service import + __all__
src/handlers/__init__.py            → 2 yeni handler import + __all__
src/bot.py                          → import, repo, service, handler, cron kaydi
```

### Slack App Dashboard

| Komut | Aciklama | Usage Hint |
|-------|---------|------------|
| `/terim` | Glossary'e yeni terim/konu gonder | `<terim_adi>` |
| `/acikla` | Bir terime aciklama ekle | `<terim> \| <aciklama>` |
| `/glossary` | Terimin detayini goruntule | `<terim_adi>` |
| `/quiz` | 3 soruluk bilgi yarismasi baslat | (bos) |

---

## 9. Gelecek Asamalar (Bu Tasarimin Disinda)

- Kahoot tarzi canli cok oyunculu quiz (web app)
- Kim Milyoner Olmak Ister tarzi artan zorluklu quiz (web app)
- Glossary istatistik dashboardu
- Terim onerme sistemi (AI tarafindan otomatik terim onerisi)
