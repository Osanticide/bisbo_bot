import discord

from discord import app_commands
from discord.ext import commands


class Ping(commands.Cog):
    """Comandos básicos de teste do Bisbo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ping", description="Verifica se o Bisbo está respondendo."
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong! carente dms vc...")


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
