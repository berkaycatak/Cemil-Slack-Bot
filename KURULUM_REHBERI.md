# Cemil Bot - Sifirdan Kurulum Rehberi

Bu rehber, Cemil Bot'u sifirdan kurup calistirmak icin gereken **tum adimlari** detaylica aciklar. Slack uygulama olusturma, API anahtarlari alma, proje kurulumu ve bot'u baslatma gibi her adim ekran ekran anlatilmaktadir.

---

## Icindekiler

1. [Gereksinimler](#1-gereksinimler)
2. [Slack Workspace Olusturma (Opsiyonel)](#2-slack-workspace-olusturma)
3. [Slack Uygulamasi Olusturma](#3-slack-uygulamasi-olusturma)
4. [Socket Mode Aktif Etme](#4-socket-mode-aktif-etme)
5. [App-Level Token (xapp) Alma](#5-app-level-token-alma)
6. [Bot Token Scopes (Yetkiler)](#6-bot-token-scopes)
7. [Bot'u Workspace'e Yukleme](#7-botu-workspacee-yukleme)
8. [Slash Komutlari Olusturma](#8-slash-komutlari-olusturma)
9. [Interactivity (Etkilesimlilik) Aktif Etme](#9-interactivity-aktif-etme)
10. [Event Subscriptions](#10-event-subscriptions)
11. [Groq API Key Alma](#11-groq-api-key-alma)
12. [Gmail SMTP Ayarlari (Opsiyonel)](#12-gmail-smtp-ayarlari)
13. [Proje Kurulumu (Kod Tarafi)](#13-proje-kurulumu)
14. [.env Dosyasi Hazirlama](#14-env-dosyasi-hazirlama)
15. [Bilgi Kupusu Hazirlama (RAG)](#15-bilgi-kupusu-hazirlama)
16. [Kullanici CSV Dosyasi Hazirlama](#16-kullanici-csv-dosyasi-hazirlama)
17. [Bot'u Baslatma](#17-botu-baslatma)
18. [Bot'u Kanallara Davet Etme](#18-botu-kanallara-davet-etme)
19. [Ilk Test: Komutlari Deneme](#19-ilk-test-komutlari-deneme)
20. [Sorun Giderme](#20-sorun-giderme)
21. [Ek: Tum Komutlar ve Ozellikler Tablosu](#21-ek-komutlar-tablosu)

---

## 1. Gereksinimler

Baslamadan once asagidakilerin hazir oldugundan emin olun:

| Gereksinim | Aciklama |
|---|---|
| **Python 3.10+** | `python3 --version` ile kontrol edin |
| **pip** | Python paket yoneticisi (`pip --version`) |
| **Git** | Projeyi klonlamak icin (`git --version`) |
| **Slack Hesabi** | Admin yetkisine sahip bir workspace |
| **Groq Hesabi** | Ucretsiz - AI ozellikleri icin gerekli |
| **Gmail Hesabi** | Opsiyonel - Anonim geri bildirim e-posta icin |
| **Internet Baglantisi** | Slack API ve Groq API ile iletisim icin |

### Python Kurulumu (Yuklu degilse)

**macOS:**
```bash
brew install python3
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
```

**Windows:**
https://www.python.org/downloads/ adresinden indirip kurun. Kurulum sirasinda "Add Python to PATH" kutusunu isaretleyin.

---

## 2. Slack Workspace Olusturma

> Zaten bir Slack workspace'iniz varsa bu adimi atlayin.

1. https://slack.com/get-started#/createnew adresine gidin
2. E-posta adresinizi girin ve dogrulama kodunu onaylayin
3. Workspace adini girin (ornegin: "Yapay Zeka Akademisi")
4. Workspace'e bir kanal ekleyin (varsayilan `#general` yeterli)
5. Workspace olusturulduktan sonra admin olarak giris yapin

---

## 3. Slack Uygulamasi Olusturma

Bu adim kritik - bot'un Slack ile konusabilmesi icin bir "App" olusturmaniz gerekiyor.

### Adim 3.1: Slack API Sayfasina Git
1. Tarayicinizda **https://api.slack.com/apps** adresine gidin
2. Sag ustteki **"Create New App"** butonuna tiklayin

### Adim 3.2: Olusturma Yontemi Sec
1. **"From scratch"** secenegini tiklayin (manifest degil)
2. Asagidaki bilgileri doldurun:
   - **App Name:** `Cemil Bot`
   - **Pick a workspace:** Workspace'inizi secin
3. **"Create App"** butonuna tiklayin

### Adim 3.3: Temel Bilgiler Sayfasi
Uygulama olusturulduktan sonra **"Basic Information"** sayfasina yonlendirileceksiniz. Bu sayfayi acik tutun - ileride lazim olacak.

---

## 4. Socket Mode Aktif Etme

Cemil Bot, **Socket Mode** ile calisir. Bu mod, bot'un Slack'e WebSocket uzerinden baglanmasini saglar ve public URL gerektirmez.

1. Sol menuden **"Socket Mode"** tiklayin
2. **"Enable Socket Mode"** toggle'ini **ON** yapin
3. Bir token ismi girin: `cemil-bot-socket`
4. **"Generate"** butonuna tiklayin
5. Olusturulan token'i (xapp-... ile baslayan) **hemen kopyalayin ve bir yere not edin**

> **ONEMLI:** Bu token `SLACK_APP_TOKEN` olarak `.env` dosyaniza yazilacak.

```
Ornek Token: xapp-1-A07XXXXXXXX-7XXXXXXXXX-abcdef1234567890...
```

---

## 5. App-Level Token Alma

Socket Mode tokeni zaten 4. adimda aldiysiniz. Buna ek olarak **Bot User OAuth Token** gerekli:

1. Sol menuden **"OAuth & Permissions"** tiklayin
2. Sayfayi asagi kaydir, **"Bot User OAuth Token"** kisminda henuz token yoksa 6. adimdan sonra goreceksiniz
3. Bu token `xoxb-...` ile baslar ve `SLACK_BOT_TOKEN` olarak kullanilir

---

## 6. Bot Token Scopes (Yetkiler)

Bot'un Slack'teki islemleri yapabilmesi icin izinler (scope) tanimlanmalidir.

### Adim 6.1: Scopes Sayfasina Git
1. Sol menuden **"OAuth & Permissions"** tiklayin
2. Sayfayi asagiya kaydir, **"Scopes"** bolumunu bulun
3. **"Bot Token Scopes"** altindaki **"Add an OAuth Scope"** butonuna tiklayin

### Adim 6.2: Asagidaki Scope'lari Tek Tek Ekleyin

Her birini arama kutusuna yazin ve secin:

| Scope | Ne Ise Yarar |
|---|---|
| `chat:write` | Kanallara mesaj gonderme, guncelleme, silme |
| `links:read` | Mesaj permalink ve link onizleme |
| `channels:read` | Kanal bilgilerini okuma |
| `channels:manage` | Kanal olusturma, arsivleme, yonetme |
| `channels:history` | Kanal mesaj gecmisini okuma |
| `groups:read` | Ozel kanal bilgilerini okuma |
| `groups:write` | Ozel kanal olusturma ve yonetme |
| `groups:history` | Ozel kanal mesaj gecmisini okuma |
| `users:read` | Kullanici bilgilerini okuma |
| `im:write` | DM (ozel mesaj) gonderme |
| `mpim:write` | Grup DM olusturma |
| `commands` | Slash komutlarini kullanma |
| `files:write` | Dosya yukleme |
| `files:read` | Dosya bilgilerini okuma |
| `pins:write` | Mesajlari sabitleme |
| `pins:read` | Sabitlenmis mesajlari okuma |
| `reactions:read` | Emoji tepkilerini okuma |

> **Not:** Tum scope'lari ekledikten sonra sayfanin ustundeki **"Install to Workspace"** butonuna tiklayin (veya 7. adima gecin).

---

## 7. Bot'u Workspace'e Yukleme

Scope'lari ekledikten sonra bot'u workspace'inize kurmaniz gerekiyor:

1. **"OAuth & Permissions"** sayfasinin en ustunde **"Install to Workspace"** (veya **"Reinstall to Workspace"**) butonuna tiklayin
2. Izin ekraninda **"Allow"** (Izin Ver) butonuna tiklayin
3. Basarili kurulumdan sonra **"Bot User OAuth Token"** gorunecek
4. Bu tokeni kopyalayin (`xoxb-...` ile baslar)

```
Ornek Token: xoxb-7XXXXXXXXX-7XXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXX
```

> **ONEMLI:** Bu token `SLACK_BOT_TOKEN` olarak `.env` dosyaniza yazilacak.

---

## 8. Slash Komutlari Olusturma

Cemil Bot 16 adet slash komutu kullanir. Her birini Slack API sayfasindan tanimlamaniz gerekiyor.

### Adim 8.1: Slash Commands Sayfasina Git
1. Sol menuden **"Slash Commands"** tiklayin
2. **"Create New Command"** butonuna tiklayin

### Adim 8.2: Her Komutu Olusturun

Asagidaki her komut icin ayni adimlari tekrarlayin:

> **Not:** "Request URL" alani Socket Mode'da otomatik yonetilir, bos birakabilir veya `https://placeholder.com` yazabilirsiniz.

#### Temel Komutlar

| # | Command | Short Description | Usage Hint |
|---|---|---|---|
| 1 | `/kahve` | Kahve eslesmesi baslat | *(bos birakin)* |
| 2 | `/oylama` | Anket olustur (Admin) | `[dakika] [konu] \| [secenek1] \| [secenek2]` |
| 3 | `/sor` | Bilgi kupusune soru sor | `[sorunuz]` |
| 4 | `/cemil-indeksle` | Bilgi kupusunu yeniden indeksle (Admin) | *(bos birakin)* |
| 5 | `/geri-bildirim` | Anonim geri bildirim gonder | `[kategori] [mesajiniz]` |
| 6 | `/profilim` | Profil bilgilerini goruntule | *(bos birakin)* |
| 7 | `/yardim-iste` | Yardim talebi olustur | `[konu] \| [aciklama]` |
| 8 | `/daily` | Gunluk icerik (Ingilizce/Motivasyon) | `english` veya `motivasyon` |
| 9 | `/cemil-health` | Bot saglik kontrolu | *(bos birakin)* |
| 10 | `/admin-istatistik` | Admin istatistikleri (Admin) | *(bos birakin)* |
| 11 | `/admin-basarili-projeler` | Basarili projeler listesi (Admin) | *(bos birakin)* |
| 12 | `/challenge` | Challenge Hub (Mini Hackathon) | `start [takim_buyuklugu]` veya `join` veya `status` |

#### Glossary ve Quiz Komutlari

| # | Command | Short Description | Usage Hint |
|---|---|---|---|
| 13 | `/terim` | Yeni terim onerisi gonder | `[terim adi]` |
| 14 | `/acikla` | Terime aciklama ekle | `[terim] \| [aciklama]` |
| 15 | `/glossary` | Terim detaylarini goruntule | `[terim adi]` |
| 16 | `/quiz` | Sozluk quizi baslat | *(bos birakin)* |

### Her Komut Icin Olusturma Adimlari

Ornegin `/kahve` komutu icin:

1. **"Create New Command"** tiklayin
2. Alanlari doldurun:
   - **Command:** `/kahve`
   - **Short Description:** `Kahve eslesmesi baslat`
   - **Usage Hint:** *(bos birakin)*
3. **"Save"** butonuna tiklayin
4. Diger komutlar icin ayni islemleri tekrarlayin

> **Not:** 16 komutu tek tek olusturmaniz gerekmektedir. Her biri icin "Create New Command" → bilgileri gir → "Save" dongusunu tekrarlayin.

---

## 9. Interactivity (Etkilesimlilik) Aktif Etme

Bot'taki butonlar, secim menuleri ve aksiyonlarin calismasi icin Interactivity aktif edilmelidir.

### Adim 9.1: Interactivity Sayfasina Git
1. Sol menuden **"Interactivity & Shortcuts"** tiklayin
2. **"Interactivity"** toggle'ini **ON** yapin
3. **Request URL** alani Socket Mode'da gerekli degildir; ancak alan zorunluysa `https://placeholder.com` yazin
4. **"Save Changes"** butonuna tiklayin

### Bot'un Kullandigi Action ID'ler (Referans)

Bu action ID'ler kod tarafinda tanimlidir ve Slack sayfasinda ayrica tanimlama gerektirmez. Socket Mode bu aksiyonlari otomatik yakalar. Ancak referans icin listelenmistir:

**Kahve Eslesmesi:**
- `join_coffee` - Kahve eslesmesine katil

**Oylama:**
- `poll_vote_0` ... `poll_vote_4` - Anket oy butonlari (5 secenek)

**Challenge Hub:**
- `challenge_join_button` - Challenge'a katil
- `challenge_theme_select_*` - Tema secimi
- `challenge_cancel_button` - Challenge iptal
- `challenge_join_jury_toggle` - Juri olarak katil/ayril
- `admin_approve_finish_challenge` - Admin challenge bitirme onayi
- `admin_reject_finish_challenge` - Admin challenge bitirme reddi
- `admin_finish_details` - Challenge bitirme detaylari

**Degerlendirme:**
- `evaluate_challenge_button` - Projeyi degerlendir
- `admin_approve_evaluation` - Admin degerlendirme onayi
- `admin_reject_evaluation` - Admin degerlendirme reddi

**Yardim:**
- `help_join_channel` - Yardim kanalina katil
- `help_details` - Yardim detaylarini gor

**Glossary:**
- `glossary_admin_approve` - Admin terim onayi
- `glossary_admin_reject` - Admin terim reddi
- `glossary_helpful` - Aciklamayi faydali bul (toggle)
- `daily_term_knew` - Gunluk terimi biliyordum
- `daily_term_didnt_know` - Gunluk terimi bilmiyordum

**Quiz:**
- `quiz_select_category` - Quiz kategori secimi
- `quiz_answer` - Quiz cevabi

---

## 10. Event Subscriptions

Bazi ozellikler icin Slack event'lerine abone olmaniz gerekir.

### Adim 10.1: Event Subscriptions Sayfasina Git
1. Sol menuden **"Event Subscriptions"** tiklayin
2. **"Enable Events"** toggle'ini **ON** yapin

### Adim 10.2: Bot Events Ekle
**"Subscribe to bot events"** bolumune asagidaki event'leri ekleyin:

| Event | Aciklama |
|---|---|
| `member_joined_channel` | Challenge kanalina yetkisiz katilim kontrolu |
| `member_left_channel` | Degerlendirme kanalindan ayrilan kullanici takibi |
| `message.channels` | Challenge kanallarinda "bitir" mesaji algilama |

### Adim 10.3: Kaydet
**"Save Changes"** butonuna tiklayin.

> **Not:** Event ekledikten sonra Slack, bot'u workspace'e yeniden yuklemek isteyebilir. "Reinstall your app" uyarisini gorurseniz tiklayin ve izin verin.

---

## 11. Groq API Key Alma

Cemil Bot, yapay zeka ozellikleri (RAG, challenge uretimi, quiz, terim dogrulama vb.) icin **Groq API** kullanir.

### Adim 11.1: Groq Hesabi Olusturma
1. https://console.groq.com adresine gidin
2. **"Sign Up"** ile ucretsiz hesap olusturun (Google veya GitHub ile giris yapabilirsiniz)

### Adim 11.2: API Key Olusturma
1. Giris yaptiktan sonra sol menuden **"API Keys"** tiklayin
2. **"Create API Key"** butonuna tiklayin
3. **Name:** `cemil-bot`
4. **"Submit"** tiklayin
5. Olusturulan anahtari kopyalayin (`gsk_...` ile baslar)

```
Ornek Key: gsk_abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGH
```

> **ONEMLI:** Bu anahtar `GROQ_API_KEY` olarak `.env` dosyaniza yazilacak. Groq ucretsiz katmanda saniyede 30 istek limiti vardir; topluluk bot'u icin yeterlidir.

---

## 12. Gmail SMTP Ayarlari (Opsiyonel)

> Bu adim **opsiyoneldir**. Sadece anonim geri bildirim ozelliginin e-posta ile de iletilmesini istiyorsaniz yapin.

Geri bildirimler Slack DM uzerinden de iletilebilir, e-posta sart degildir.

### Adim 12.1: Gmail Hesabi Hazirlama
1. Bot icin ayri bir Gmail hesabi olusturun (ornegin: `cemilbot.akademi@gmail.com`)
2. Veya mevcut Gmail hesabinizi kullanin

### Adim 12.2: 2 Adimli Dogrulama Aktif Etme
1. https://myaccount.google.com/security adresine gidin
2. **"2-Step Verification"** (2 Adimli Dogrulama) aktif edin

### Adim 12.3: App Password (Uygulama Sifresi) Olusturma
1. https://myaccount.google.com/apppasswords adresine gidin
2. **App name:** `Cemil Bot` yazin
3. **"Create"** tiklayin
4. 16 haneli sifreyi kopyalayin (bosluklar olmadan)

```
Ornek: abcd efgh ijkl mnop → abcdefghijklmnop
```

> **ONEMLI:** `SMTP_EMAIL` ve `SMTP_PASSWORD` olarak `.env` dosyaniza yazilacak.

---

## 13. Proje Kurulumu

### Adim 13.1: Projeyi Klonlayin

```bash
git clone https://github.com/KULLANICI_ADINIZ/cemil-bot.git
cd cemil-bot
```

### Adim 13.2: Sanal Ortam (Virtual Environment) Olusturun

```bash
# Sanal ortam olustur
python3 -m venv .venv

# Aktif et
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

Basarili aktivasyondan sonra terminal satirinda `(.venv)` goreceksiniz:
```
(.venv) user@pc:~/cemil-bot$
```

### Adim 13.3: Bagimlilik Yukleyin

```bash
pip install -r requirements.txt
```

Bu islem tum bagimliliklari yukler. Ilk seferde biraz zaman alabilir (~2-5 dakika), ozellikle `sentence-transformers` ve `torch` buyuk paketlerdir.

**Yuklenen temel kutuphaneler:**

| Paket | Gorevi |
|---|---|
| `slack-bolt` | Slack Bot Framework (Socket Mode) |
| `slack-sdk` | Slack API Python SDK |
| `groq` | Groq AI API istemcisi |
| `pydantic` / `pydantic-settings` | Veri dogrulama ve ayar yonetimi |
| `sentence-transformers` | Metin embedding'leri (RAG) |
| `faiss-cpu` | Vektor benzerlik arama (RAG) |
| `langchain-text-splitters` | Dokuman parcalama (RAG) |
| `pypdf` / `python-docx` | PDF ve Word dosyasi okuma |
| `pandas` | CSV islemleri |
| `rich` | Terminal ciktisi formatlama |
| `apscheduler` | Zamanlanmis gorevler (cron jobs) |

### Adim 13.4: Klasor Yapisini Dogrulayin

```bash
ls -la
```

Asagidaki yapiyi gormelisiniz:
```
cemil-bot/
├── src/                  # Bot kaynak kodu
│   ├── bot.py            # Ana bot dosyasi
│   ├── __main__.py       # Baslangic noktasi
│   ├── core/             # Logger, settings, exceptions
│   ├── clients/          # DB, Groq, Slack, SMTP istemcileri
│   ├── commands/         # Slack API wrapper siniflar
│   ├── repositories/     # Veritabani erisim katmani
│   ├── services/         # Is mantigi katmani
│   └── handlers/         # Slash komut isleyicileri
├── data/                 # Veritabani ve CSV dosyalari (otomatik olusur)
├── knowledge_base/       # RAG icin dokumanlar (otomatik olusur)
├── logs/                 # Log dosyalari (otomatik olusur)
├── migrations/           # SQL migration dosyalari
├── scripts/              # Yardimci scriptler
├── tests/                # Test dosyalari
├── .env.example          # Ornek cevresel degiskenler
├── requirements.txt      # Python bagimliliklari
└── README.md             # Proje aciklamasi
```

---

## 14. .env Dosyasi Hazirlama

### Adim 14.1: .env Dosyasini Olusturun

```bash
cp .env.example .env
```

### Adim 14.2: .env Dosyasini Duzenleyin

Favori metin duzenleyicinizle acin:
```bash
# macOS/Linux:
nano .env

# veya VS Code ile:
code .env
```

### Adim 14.3: Degerleri Doldurun

Asagidaki sablonu kendi degerlerinizle doldurun:

```env
# ==============================
# ZORUNLU AYARLAR
# ==============================

# Slack API Token'lari (Adim 4 ve 7'den aldiginiz tokenler)
SLACK_BOT_TOKEN=xoxb-BURAYA-BOT-TOKENINIZI-YAPIN
SLACK_APP_TOKEN=xapp-BURAYA-APP-TOKENINIZI-YAPIN

# Groq API Key (Adim 11'den aldiginiz key)
GROQ_API_KEY=gsk_BURAYA-GROQ-KEYINIZI-YAPIN

# ==============================
# ONERILEN AYARLAR
# ==============================

# Bot baslangic mesajini gonderdigi kanal
SLACK_STARTUP_CHANNEL=#general

# Admin kanalinin ID'si (Admin bildirimlerinin gittigi kanal)
# Kanal ID'sini bulmak: Slack'te kanala sag tikla → "View channel details" → en altta ID
ADMIN_CHANNEL_ID=C0XXXXXXXXX

# Admin kullanicinin Slack ID'si
# ID bulmak: Slack'te profil resmine tikla → "..." → "Copy member ID"
ADMIN_SLACK_ID=U0XXXXXXXXX

# Glossary gunluk bulten kanali (serbest-kursu gibi bir kanal)
GLOSSARY_DAILY_CHANNEL=C0XXXXXXXXX

# ==============================
# OPSIYONEL AYARLAR
# ==============================

# GitHub Repo URL'si (baslangic mesajinda gosterilir)
GITHUB_REPO=https://github.com/KULLANICI_ADINIZ/cemil-bot

# E-posta (Anonim geri bildirim icin - Adim 12'deki bilgiler)
SMTP_EMAIL=cemilbot@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
ADMIN_EMAIL=admin@example.com

# Veritabani dosya yolu (varsayilan: data/cemil_bot.db)
DB_PATH=data/cemil_bot.db

# Log seviyesi (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Glossary otomatik onay esigi (AI skoru bu ve uzeri ise otomatik onaylanir)
GLOSSARY_AUTO_APPROVE_THRESHOLD=7.0

# ==============================
# BASLANGIÇ OTOMASYONU (True/False)
# ==============================

# Bot basladiginda challenge tablolarini temizle
DB_CLEAN_ON_STARTUP=false

# Bot basladiginda CSV'den kullanici ice aktar
DB_IMPORT_INITIAL_USERS=false

# Bot basladiginda vektor indeksini yeniden olustur
KB_REBUILD_INDEX=false

# Bot basladiginda hosgeldin mesaji gonder
SLACK_SEND_WELCOME_MESSAGE=false
```

### Kanal ve Kullanici ID'lerini Bulmak

**Kanal ID bulma:**
1. Slack'te kanala gidin
2. Kanal adina tiklayin (ustteki baslik)
3. Acilan panelin en altinda `Channel ID: C0XXXXXXXXX` yazar

**Kullanici ID bulma:**
1. Slack'te kullanicinin profil resmine tiklayin
2. **"..."** (uc nokta) butonuna tiklayin
3. **"Copy member ID"** secin

---

## 15. Bilgi Kupusu Hazirlama (RAG)

Bot'un `/sor` komutuyla sorulara cevap verebilmesi icin `knowledge_base/` klasorune dokumanlar yerlestirmeniz gerekir.

### Desteklenen Formatlar

| Format | Uzanti |
|---|---|
| PDF | `.pdf` |
| Word | `.docx` |
| Duz Metin | `.txt` |
| Markdown | `.md` |
| Excel | `.xlsx` |
| CSV | `.csv` |

### Ornek Klasor Yapisi

```bash
mkdir -p knowledge_base
```

Dokumanlarinizi bu klasore kopyalayin:
```
knowledge_base/
├── akademi_kurallari.pdf
├── burs_politikasi.docx
├── sss.md
└── egitim_programi.txt
```

> **Not:** Bot ilk baslatildiginda bu dokumanlari otomatik olarak indeksler ve vektor veritabanina kaydeder. Sonraki baslatmalarda mevcut indeks kullanilir. Yeniden indekslemek icin `/cemil-indeksle` komutunu kullanin veya `.env` dosyasinda `KB_REBUILD_INDEX=true` yapin.

---

## 16. Kullanici CSV Dosyasi Hazirlama

Bot, topluluk uyelerinin bilgilerini veritabaninda tutar. Baslangiçta toplu kullanici yuklemek icin CSV dosyasi kullanabilirsiniz.

### CSV Formati

`data/initial_users.csv` dosyasini olusturun:

```csv
Slack ID,First Name,Surname,Full Name,Birthday,Cohort
U01ABC123,Ahmet,Yilmaz,Ahmet Yilmaz,15.03.1995,Yapay Zeka 1. Donem
U02DEF456,Ayse,Kaya,Ayse Kaya,22.07.1998,Veri Bilimi 2. Donem
U03GHI789,Mehmet,Demir,Mehmet Demir,01.12.1992,Derin Ogrenme 3. Donem
```

**Onemli:**
- `Slack ID` her kullanicinin benzersiz Slack kimligidir (U ile baslar)
- `Birthday` formati: `GG.AA.YYYY`
- `Cohort` kullanicinin bulundugu grubu/donemi belirtir

> **Not:** Bu dosya opsiyoneldir. Dosya yoksa bot otomatik bir sablon olusturur. Kullanicilar `/profilim` veya `/kayit` komutuyla kendi bilgilerini de girebilir.

---

## 17. Bot'u Baslatma

### Adim 17.1: Sanal Ortamin Aktif Oldugunu Dogrulayin

```bash
# (.venv) gorunuyor olmali
source .venv/bin/activate   # gerekirse
```

### Adim 17.2: Bot'u Baslatin

**Yontem 1: Modul olarak (Onerilen)**
```bash
python3 -m src
```

**Yontem 2: Dogrudan**
```bash
python3 src/bot.py
```

### Beklenen Cikti

```
[INIT] Cemil Bot baslatiliyor...
[INIT] Gerekli yapay zeka kutuphaneleri yukleniyor...

============================================================
           CEMIL BOT - HIZLI BASLATMA (PROD)
============================================================

[>] Veritabani kontrol ediliyor...
[+] Veritabani semasi guncel.

[i] 'data/initial_users.csv' dosyasi bulundu.
[i] CSV verileri otomatik ice aktariliyor...
[+] Basarili! 3 kullanici eklendi.

[>] Zamanlanmis gorevler baslatiliyor...
[i] Mevcut vektor veritabani kullaniliyor.

============================================================
           BOT CALISIYOR - CTRL+C ile durdurun
============================================================

[i] Slack baglantisi kuruluyor...
[+] Bot Slack'e baglandi ve komutlari dinliyor!
```

### Bot'u Durdurmak

```
CTRL+C
```

Bot, **graceful shutdown** ile guvenli bir sekilde kapanir:
- Slack baglantisini kapatir
- Zamanlanmis gorevleri durdurur
- Veritabani baglantilarini temizler

---

## 18. Bot'u Kanallara Davet Etme

Bot'un bir kanalda komutlara yanit verebilmesi icin o kanala **davet edilmesi** gerekir.

### Davet Yontemi

Her kanalda asagidaki adimi uygulayin:

1. Slack'te kanala gidin (ornegin `#general`)
2. Mesaj kutusuna yazip gonderin:
   ```
   /invite @Cemil Bot
   ```
   veya kanal ayarlarindan "Add members" ile bot'u ekleyin

### Hangi Kanallara Davet Etmeli?

| Kanal | Neden |
|---|---|
| `#general` | Baslangic mesaji, kahve eslesmesi, yardim ilanlarim dogum gunu kutlamalari |
| `#admin` (veya admin kanaliniz) | Admin bildirimleri (terim onayi, geri bildirimler) |
| `#serbest-kursu` (veya sozluk kanali) | Gunluk glossary bulteni |
| Challenge kanallari | Otomatik olusturulur, bot kendini davet eder |

---

## 19. Ilk Test: Komutlari Deneme

Bot basaryla basladiktan sonra her ozelligi test edin:

### Test 1: Saglik Kontrolu
```
/cemil-health
```
**Beklenen:** Bot, veritabani, Groq API ve vektor store durumunu gosteren bir mesaj gonderir.

### Test 2: Profil Goruntuleme
```
/profilim
```
**Beklenen:** Kayitli bilgilerinizi gosteren bir mesaj (veya kayitli degilseniz uyari).

### Test 3: Kahve Eslesmesi
```
/kahve
```
**Beklenen:** "Isteginiz alindi, eslesme bekleniyor..." gibi bir ephemeral mesaj.

### Test 4: Bilgi Kupusu
```
/sor Akademi kurallari nelerdir?
```
**Beklenen:** knowledge_base klasorundeki dokumanlardan cevap (dokuman yoksa bilgi bulunamadi mesaji).

### Test 5: Gunluk Icerik
```
/daily english
```
**Beklenen:** Yapay zeka tarafindan uretilmis Ingilizce pratik mesaji.

### Test 6: Terim Onerisi
```
/terim Gradient Descent
```
**Beklenen:** AI terimi degerlendirir, skora gore otomatik onay veya admin'e bildirim gonderir.

### Test 7: Quiz
```
/quiz
```
**Beklenen:** Kategori secim menusu (en az 5 onaylanmis terim gerektirir).

---

## 20. Sorun Giderme

### Hata: "SLACK_BOT_TOKEN environment variable is required!"

**Cozum:** `.env` dosyanizda `SLACK_BOT_TOKEN` dogru ayarlanmis mi kontrol edin. Token `xoxb-` ile baslamali.

```bash
# .env dosyasini kontrol edin:
cat .env | grep SLACK_BOT_TOKEN
```

### Hata: "SLACK_APP_TOKEN eksik!"

**Cozum:** `.env` dosyanizda `SLACK_APP_TOKEN` dogru ayarlanmis mi kontrol edin. Token `xapp-` ile baslamali.

### Hata: "dispatch_failed" veya Slash komut calisimiyor

**Olasi Nedenler:**
1. Slash komutu Slack API sayfasinda tanimlanmamis → Adim 8'i tekrarlayin
2. Bot workspace'e yeniden yuklenmemis → "OAuth & Permissions" → "Reinstall to Workspace"
3. Bot kanala davet edilmemis → Adim 18'i uygulayin

### Hata: "missing_scope" veya Yetki hatasi

**Cozum:**
1. https://api.slack.com/apps adresine gidin
2. Uygulamanizi secin
3. "OAuth & Permissions" → "Scopes" → Eksik scope'u ekleyin
4. **"Reinstall to Workspace"** tiklayin (scope degisikligi sonrasi zorunlu)

### Hata: Groq API hatasi

**Olasi Nedenler:**
1. `GROQ_API_KEY` yanlis veya suresi dolmus → Groq Console'dan yeni key olusturun
2. Rate limit asilmis → Birkaç saniye bekleyip tekrar deneyin
3. Internet baglantisi yok → Baglantinizi kontrol edin

### Hata: "no such table" veya veritabani hatasi

**Cozum:**
```bash
# Veritabanini sifirla (dikkat: tum veriler silinir)
rm data/cemil_bot.db
python3 -m src
```

### Log Dosyasini Kontrol Etme

Detayli hata bilgisi icin log dosyasini inceleyin:

```bash
# Son 50 satiri gor
tail -50 logs/cemil_detailed.log

# Canli takip (bot calisirken)
tail -f logs/cemil_detailed.log

# Sadece hatalari filtrele
grep "ERROR\|HATA\|Exception" logs/cemil_detailed.log
```

### Bot Slack'e Baglanamiyorsa

1. **Socket Mode aktif mi?** → Adim 4'u kontrol edin
2. **Token'lar dogru mu?** → `xoxb-` (bot) ve `xapp-` (app) ile baslamali
3. **Internet baglantisi var mi?** → `ping api.slack.com`
4. **Firewall/VPN engeli var mi?** → WebSocket baglantilarina izin verin

---

## 21. Ek: Tum Komutlar ve Ozellikler Tablosu

### Slash Komutlari

| Komut | Aciklama | Kim Kullanabilir | Ornek |
|---|---|---|---|
| `/kahve` | Kahve eslesmesi baslat | Herkes | `/kahve` |
| `/oylama` | Anket olustur | Admin | `/oylama 30 Etkinlik? \| Bowling \| Sinema` |
| `/sor` | Bilgi kupusune soru sor | Herkes | `/sor Yillik izin hakki nedir?` |
| `/cemil-indeksle` | Bilgi kupusunu yeniden indeksle | Admin | `/cemil-indeksle` |
| `/geri-bildirim` | Anonim geri bildirim gonder | Herkes | `/geri-bildirim yemekhane Yemekler soguk` |
| `/profilim` | Profil goruntule | Herkes | `/profilim` |
| `/yardim-iste` | Yardim talebi olustur | Herkes | `/yardim-iste Python \| async anlamiyorum` |
| `/daily` | Gunluk icerik | Herkes | `/daily english` veya `/daily motivasyon` |
| `/cemil-health` | Bot saglik kontrolu | Herkes | `/cemil-health` |
| `/admin-istatistik` | Istatistikleri gor | Admin | `/admin-istatistik` |
| `/admin-basarili-projeler` | Basarili projeleri listele | Admin | `/admin-basarili-projeler` |
| `/challenge` | Challenge Hub | Herkes | `/challenge start 4` |
| `/terim` | Yeni terim oner | Herkes | `/terim Backpropagation` |
| `/acikla` | Terime aciklama ekle | Herkes | `/acikla Docker \| Konteyner teknolojisi` |
| `/glossary` | Terim detayi gor | Herkes | `/glossary Transformer` |
| `/quiz` | Sozluk quizi baslat | Herkes | `/quiz` |

### Zamanlanmis Gorevler (Otomatik)

| Gorev | Zamanlama | Aciklama |
|---|---|---|
| Dogum gunu kontrolu | Her gun 09:00 | Dogum gunu olan kullanicilari kutlar |
| Glossary gunluk bulten | Her gun 09:00 | Serbest-kursu kanalina terim bulteni gonderir |
| Challenge kanal kontrolu | Her 1 dakika | Yetkisiz kullanicilari challenge kanallarindan cikarir |
| Degerlendirme kontrolu | Her saat basi | Suresi dolmus degerlendirmeleri tamamlar |
| Recruitment timeout | Her gun 03:00 | Takimi dolmayan challenge'lari iptal eder |

### Mimari Katmanlar

```
Kullanici (Slack) → Slash Komut
        ↓
    Handler (komut isleyici)
        ↓
    Service (is mantigi + AI)
        ↓
    Repository (veritabani sorgu)
        ↓
    Client (DB, Groq, Slack API)
```

---

## Hizli Baslangiç Ozeti (TL;DR)

Tum yukaridaki adimlari ozetleyen hizli kontrol listesi:

```
[ ] 1. Python 3.10+ yuklu
[ ] 2. Slack workspace hazir
[ ] 3. api.slack.com/apps'dan uygulama olusturuldu
[ ] 4. Socket Mode aktif + xapp token alindi
[ ] 5. Bot Token Scopes eklendi (17 adet)
[ ] 6. Bot workspace'e yuklendi + xoxb token alindi
[ ] 7. 16 slash komutu tanimlandi
[ ] 8. Interactivity aktif edildi
[ ] 9. Event Subscriptions eklendi (3 event)
[ ] 10. Groq API key alindi
[ ] 11. Proje klonlandi ve bagimliliklar yuklendi
[ ] 12. .env dosyasi dolduruldu
[ ] 13. Bot baslatildi: python3 -m src
[ ] 14. Bot kanallara davet edildi
[ ] 15. /cemil-health ile test edildi
```

---

*Bu rehber Cemil Bot v1.0 icin hazirlanmistir. Sorulariniz icin GitHub Issues kullanin.*
