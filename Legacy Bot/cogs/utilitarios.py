import discord
from discord import app_commands
from discord.ext import commands

# Criamos a classe que o main.py vai carregar
class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Este é um Slash Command (Comando de Barra)
    @app_commands.command(name="ping", description="Mostra a latência da Cindy")
    async def ping(self, interaction: discord.Interaction):
        # Em comandos de barra, usamos interaction.response em vez de ctx.send
        latencia = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latência: {latencia}ms")

# Esta função é essencial para o Cog funcionar
async def setup(bot):
    await bot.add_cog(Utilitarios(bot))