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

    message_count INTEGER NOT NULL DEFAULT 0
        CONSTRAINT profiles_message_count_range
        CHECK (message_count >= 0 AND message_count < 5),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Adiciona message_count caso a tabela profiles já exista.
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS message_count INTEGER NOT NULL DEFAULT 0;

-- Adiciona a restrição somente se ela ainda não existir.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'profiles_message_count_range'
          AND conrelid = 'profiles'::regclass
    ) THEN
        ALTER TABLE profiles
        ADD CONSTRAINT profiles_message_count_range
        CHECK (message_count >= 0 AND message_count < 5);
    END IF;
END;
$$;
"""
