-- Migration 004: Glossary ve Quiz tablolari
-- Tarih: 2026-02-18
-- Aciklama: Topluluk glossary sistemi ve quiz ozelligi icin 7 yeni tablo

-- Glossary Terms (Terimler)
CREATE TABLE IF NOT EXISTS glossary_terms (
    id              TEXT PRIMARY KEY,
    term            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,
    term_type       TEXT NOT NULL DEFAULT 'term',
    related_terms   TEXT,
    ai_score        REAL NOT NULL DEFAULT 0.0,
    status          TEXT NOT NULL DEFAULT 'pending',
    submitted_by    TEXT NOT NULL,
    ai_validation   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_status ON glossary_terms(status);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_category ON glossary_terms(category);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_term ON glossary_terms(term);

-- Glossary Definitions (Aciklamalar)
CREATE TABLE IF NOT EXISTS glossary_definitions (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,
    definition      TEXT NOT NULL,
    contributor_id  TEXT NOT NULL,
    helpful_count   INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
    FOREIGN KEY (contributor_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_glossary_definitions_term ON glossary_definitions(term_id);

-- Glossary Reactions (Aciklama Tepkileri)
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

-- Daily Term Logs (Gunluk Terim Gonderileri)
CREATE TABLE IF NOT EXISTS daily_term_logs (
    id              TEXT PRIMARY KEY,
    term_id         TEXT NOT NULL,
    post_type       TEXT NOT NULL,
    message_ts      TEXT,
    channel_id      TEXT,
    posted_at       DATE NOT NULL,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_daily_term_logs_date ON daily_term_logs(posted_at);

-- Daily Term Reactions (Gunluk Terim Tepkileri)
CREATE TABLE IF NOT EXISTS daily_term_reactions (
    id              TEXT PRIMARY KEY,
    daily_log_id    TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    reaction_type   TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(daily_log_id, user_id),
    FOREIGN KEY (daily_log_id) REFERENCES daily_term_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);

-- Quiz Sessions (Quiz Oturumlari)
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    category        TEXT NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 3,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    wrong_count     INTEGER NOT NULL DEFAULT 0,
    score           INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'in_progress',
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(slack_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_score ON quiz_sessions(score DESC);

-- Quiz Answers (Quiz Cevaplari)
CREATE TABLE IF NOT EXISTS quiz_answers (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    options         TEXT NOT NULL,
    correct_answer  TEXT NOT NULL,
    user_answer     TEXT,
    is_correct      BOOLEAN,
    answered_at     TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_session ON quiz_answers(session_id);
