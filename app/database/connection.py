import os

import asyncpg

from app.database.schema import PROFILE_TABLE_SQL, JOBS_TABLE_SQL


class Database:
    """Gerencia o pool de conexões com o PostgreSQL."""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Cria o pool de conexões com o banco."""

        if self.pool is not None:
            return

        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("A variável DATABASE_URL não foi configurada.")

        self.pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )

        print("[DATABASE] Pool de conexões criado.")

    async def initialize(self):
        """Prepara a estrutura inicial do banco."""

        if self.pool is None:
            raise RuntimeError("O banco ainda não foi conectado.")

        async with self.pool.acquire() as connection:
            await connection.execute(PROFILE_TABLE_SQL)
            await connection.execute(JOBS_TABLE_SQL)

        print("[DATABASE] Estrutura inicial verificada.")

    async def close(self):
        """Encerra o pool de conexões."""

        if self.pool is not None:
            await self.pool.close()
            self.pool = None

            print("[DATABASE] Conexões encerradas.")
