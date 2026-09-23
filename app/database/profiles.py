import asyncpg


class ProfileRepository:
    """Executa operações relacionadas aos perfis."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_profile(self, user_id: int):
        query = "SELECT * FROM profiles WHERE user_id = $1;"
        return await self.pool.fetchrow(query, user_id)

    async def get_or_create_profile(self, user_id: int):
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO profiles (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING;
                """,
                user_id,
            )
            return await connection.fetchrow(
                "SELECT * FROM profiles WHERE user_id = $1;",
                user_id,
            )

    async def register_valid_message(self, user_id: int) -> dict:
        """
        Registra uma mensagem válida. A cada 5 mensagens, concede 10 XP.
        A atualização é transacional e mantém a contagem parcial no PostgreSQL.
        """
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO profiles (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    user_id,
                )

                row = await connection.fetchrow(
                    """
                    SELECT level, xp, message_count
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE;
                    """,
                    user_id,
                )

                count = row["message_count"] + 1
                earned_xp = 0
                levels_gained = 0
                level = row["level"]
                xp = row["xp"]

                if count >= 5:
                    count = 0
                    earned_xp = 10
                    xp += earned_xp

                    while xp >= 20 * level:
                        xp -= 20 * level
                        level += 1
                        levels_gained += 1

                await connection.execute(
                    """
                    UPDATE profiles
                    SET message_count = $2,
                        level = $3,
                        xp = $4,
                        updated_at = NOW()
                    WHERE user_id = $1;
                    """,
                    user_id,
                    count,
                    level,
                    xp,
                )

        return {
            "message_count": count,
            "earned_xp": earned_xp,
            "level": level,
            "xp": xp,
            "levels_gained": levels_gained,
        }
