import asyncpg


class ProfileRepository:
    """Executa operações relacionadas aos perfis."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_profile(self, user_id: int):
        """Busca um perfil existente."""

        query = """
        SELECT *
        FROM profiles
        WHERE user_id = $1;
        """

        return await self.pool.fetchrow(query, user_id)

    async def get_or_create_profile(self, user_id: int):
        """Busca um perfil ou cria um novo."""

        insert_query = """
        INSERT INTO profiles (user_id)
        VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING;
        """

        select_query = """
        SELECT *
        FROM profiles
        WHERE user_id = $1;
        """

        async with self.pool.acquire() as connection:
            await connection.execute(insert_query, user_id)

            profile = await connection.fetchrow(
                select_query,
                user_id,
            )

        return profile
