import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


# Carrega as variáveis do arquivo .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")


class BisboBot(commands.Bot):
    async def setup_hook(self):
        # Carrega o módulo do comando /ping
        await self.load_extension("app.cogs.ping")

        # Registra os comandos no nosso servidor
        guild = discord.Object(id=int(GUILD_ID))

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("Comandos sincronizados com o servidor Bisbo.")


# Configura as permissões de eventos que o bot receberá
intents = discord.Intents.default()


# Cria a instância principal do Bisbo
bot = BisboBot(command_prefix="!", intents=intents)


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
