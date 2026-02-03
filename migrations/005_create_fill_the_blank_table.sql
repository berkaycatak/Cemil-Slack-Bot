CREATE TABLE IF NOT EXISTS fill_the_blank_games (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    song_title TEXT,
    song_artist TEXT,
    original_lyrics TEXT,
    blanked_lyrics TEXT,
    correct_words TEXT, -- JSON list of words to fill
    status TEXT DEFAULT 'active', -- active, completed, abandoned
    score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ftb_user_status ON fill_the_blank_games(user_id, status);
