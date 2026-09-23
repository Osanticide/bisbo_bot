import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from app.database.connection import Database
from app.database.profiles import ProfileRepository


# Carrega as variáveis do arquivo .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")


class BisboBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.db = Database()
        self.profiles = None

    async def setup_hook(self):
        # Conecta ao PostgreSQL
        await self.db.connect()

        # Garante que a tabela de perfis exista
        await self.db.initialize()

        # Cria o repositório de perfis
        self.profiles = ProfileRepository(self.db.pool)

        # Carrega os comandos existentes
        await self.load_extension("app.cogs.ping")
        await self.load_extension("app.cogs.bighead")

        # adiciona o sistema de perfil
        await self.load_extension("app.cogs.profile")

        # Registra os comandos no servidor
        guild = discord.Object(id=int(GUILD_ID))

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("Comandos sincronizados com o servidor Bisbo.")

    async def close(self):
        # Encerra o banco antes de fechar o bot
        await self.db.close()

        await super().close()


# Cria a instância principal do Bisbo
bot = BisboBot()


@bot.event
async def on_ready():
    print(f"Bisbo está online como {bot.user}")


# Inicia o bot
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("O token DISCORD_TOKEN não foi configurado.")

    if not GUILD_ID:
        raise ValueError("O DISCORD_GUILD_ID não foi configurado.")

    bot.run(TOKEN)
