import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from app.database.connection import Database
from app.database.profiles import ProfileRepository
from app.services.xp import XPService

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")


class BisboBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Necessário para receber o conteúdo das mensagens no evento on_message.
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.db = Database()
        self.profiles = None
        self.xp_service = None

    async def setup_hook(self):
        await self.db.connect()
        await self.db.initialize()

        self.profiles = ProfileRepository(self.db.pool)
        self.xp_service = XPService(self.profiles)

        await self.load_extension("app.cogs.ping")
        await self.load_extension("app.cogs.bighead")
        await self.load_extension("app.cogs.profile")
        await self.load_extension("app.cogs.messages")

        guild = discord.Object(id=int(GUILD_ID))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("Comandos sincronizados com o servidor Bisbo.")

    async def close(self):
        await self.db.close()
        await super().close()


bot = BisboBot()


@bot.event
async def on_ready():
    print(f"Bisbo está online como {bot.user}")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("O token DISCORD_TOKEN não foi configurado.")
    if not GUILD_ID:
        raise ValueError("O DISCORD_GUILD_ID não foi configurado.")
    bot.run(TOKEN)
