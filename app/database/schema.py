PROFILE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id BIGINT PRIMARY KEY,

    level INTEGER NOT NULL DEFAULT 1
        CHECK (level >= 1),

    xp INTEGER NOT NULL DEFAULT 0
        CHECK (xp >= 0),

    wallet NUMERIC(20,2) NOT NULL DEFAULT 0
        CHECK (wallet >= 0),

    bank NUMERIC(20,2) NOT NULL DEFAULT 0
        CHECK (bank >= 0),

    profession TEXT DEFAULT NULL,

    profession_level INTEGER NOT NULL DEFAULT 0
        CHECK (profession_level >= 0),

    message_count INTEGER NOT NULL DEFAULT 0
        CONSTRAINT profiles_message_count_range
        CHECK (message_count >= 0 AND message_count < 5),

    daily_reward_at TIMESTAMPTZ DEFAULT NULL,
    weekly_reward_at TIMESTAMPTZ DEFAULT NULL,
    monthly_reward_at TIMESTAMPTZ DEFAULT NULL,

    bank_interest_at TIMESTAMPTZ DEFAULT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Garante a existência da coluna de contagem de mensagens.
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS message_count INTEGER NOT NULL DEFAULT 0;

-- Migra saldos BIGINT antigos para NUMERIC.
ALTER TABLE profiles
ALTER COLUMN wallet TYPE NUMERIC(20,2)
USING wallet::NUMERIC(20,2);

ALTER TABLE profiles
ALTER COLUMN bank TYPE NUMERIC(20,2)
USING bank::NUMERIC(20,2);

-- Campos de controle dos rewards.
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS daily_reward_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS weekly_reward_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS monthly_reward_at TIMESTAMPTZ DEFAULT NULL;

-- Controle da última aplicação de juros.
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS bank_interest_at TIMESTAMPTZ DEFAULT NULL;

-- Garante a restrição de message_count.
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
JOBS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,

    name TEXT NOT NULL UNIQUE,

    coefficient NUMERIC(10,4) NOT NULL
        CHECK (coefficient > 0),

    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS job_progress (
    user_id BIGINT NOT NULL
        REFERENCES profiles(user_id)
        ON DELETE CASCADE,

    job_id INTEGER NOT NULL
        REFERENCES jobs(id),

    level INTEGER NOT NULL DEFAULT 1
        CHECK (level >= 1),

    xp INTEGER NOT NULL DEFAULT 0
        CHECK (xp >= 0),

    last_work_at TIMESTAMPTZ DEFAULT NULL,

    PRIMARY KEY (user_id, job_id)
);

CREATE TABLE IF NOT EXISTS job_history (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL
        REFERENCES profiles(user_id)
        ON DELETE CASCADE,

    job_id INTEGER NOT NULL
        REFERENCES jobs(id),

    hired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    abandoned_at TIMESTAMPTZ DEFAULT NULL,

    CHECK (
        abandoned_at IS NULL
        OR abandoned_at >= hired_at
    )
);

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS current_job_id INTEGER;

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS job_hired_at TIMESTAMPTZ DEFAULT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'profiles_current_job_fk'
          AND conrelid = 'profiles'::regclass
    ) THEN
        ALTER TABLE profiles
        ADD CONSTRAINT profiles_current_job_fk
        FOREIGN KEY (current_job_id)
        REFERENCES jobs(id);
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS job_history_one_active_per_user
ON job_history(user_id)
WHERE abandoned_at IS NULL;

INSERT INTO jobs (name, coefficient)
VALUES
    ('Lenhador', 1.0000),
    ('Pescador', 1.0500),
    ('Repositor', 1.1000)
ON CONFLICT (name) DO NOTHING;
"""
