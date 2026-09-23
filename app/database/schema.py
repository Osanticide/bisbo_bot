PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id BIGINT PRIMARY KEY,

    level INTEGER NOT NULL DEFAULT 1
        CHECK (level >= 1),

    xp INTEGER NOT NULL DEFAULT 0
        CHECK (xp >= 0),

    wallet BIGINT NOT NULL DEFAULT 0
        CHECK (wallet >= 0),

    bank BIGINT NOT NULL DEFAULT 0
        CHECK (bank >= 0),

    profession TEXT DEFAULT NULL,

    profession_level INTEGER NOT NULL DEFAULT 0
        CHECK (profession_level >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
