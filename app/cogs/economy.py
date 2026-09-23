import logging

import discord
from discord import app_commands
from discord.ext import commands

from app.services.economy import (
    EconomyError,
    format_money,
    validate_amount,
)


logger = logging.getLogger(__name__)


class Economy(commands.Cog):
    """Comandos da economia do Bisbo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="saldo",
        description="Veja o saldo da sua carteira e do banco.",
    )
    @app_commands.guild_only()
    async def saldo(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        try:
            balance = await self.bot.profiles.get_balance(interaction.user.id)

            wallet = balance["wallet"]
            bank = balance["bank"]
            total = wallet + bank

            embed = discord.Embed(
                title=f"💰 Economia de {interaction.user.display_name}",
                color=discord.Color.gold(),
            )

            embed.add_field(
                name="👛 Carteira",
                value=format_money(wallet),
                inline=True,
            )

            embed.add_field(
                name="🏦 Banco",
                value=format_money(bank),
                inline=True,
            )

            embed.add_field(
                name="💎 Patrimônio total",
                value=format_money(total),
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            logger.exception(
                "Erro ao consultar saldo do usuário %s.",
                interaction.user.id,
            )
            await interaction.followup.send(
                "Não foi possível consultar seu saldo. Tente novamente.",
                ephemeral=True,
            )

    @app_commands.command(
        name="depositar",
        description="Deposite CP da carteira no banco.",
    )
    @app_commands.guild_only()
    @app_commands.describe(valor="Valor a depositar, ex.: 150 ou 12.50")
    async def depositar(
        self,
        interaction: discord.Interaction,
        valor: str,
    ):
        await interaction.response.defer(thinking=True)

        try:
            amount = validate_amount(valor)

            result = await self.bot.profiles.deposit(
                interaction.user.id,
                amount,
            )

            await interaction.followup.send(
                f"🏦 Você depositou **{format_money(amount)}**.\n"
                f"👛 Carteira: {format_money(result['wallet'])}\n"
                f"🏦 Banco: {format_money(result['bank'])}"
            )

        except EconomyError as error:
            await interaction.followup.send(str(error), ephemeral=True)

        except Exception:
            logger.exception(
                "Erro no depósito do usuário %s.",
                interaction.user.id,
            )
            await interaction.followup.send(
                "Não foi possível realizar o depósito. Tente novamente.",
                ephemeral=True,
            )

    @app_commands.command(
        name="sacar",
        description="Saque CP do banco para sua carteira.",
    )
    @app_commands.guild_only()
    @app_commands.describe(valor="Valor a sacar, ex.: 150 ou 12.50")
    async def sacar(
        self,
        interaction: discord.Interaction,
        valor: str,
    ):
        await interaction.response.defer(thinking=True)

        try:
            amount = validate_amount(valor)

            result = await self.bot.profiles.withdraw(
                interaction.user.id,
                amount,
            )

            await interaction.followup.send(
                f"💵 Você sacou **{format_money(amount)}**.\n"
                f"👛 Carteira: {format_money(result['wallet'])}\n"
                f"🏦 Banco: {format_money(result['bank'])}"
            )

        except EconomyError as error:
            await interaction.followup.send(str(error), ephemeral=True)

        except Exception:
            logger.exception(
                "Erro no saque do usuário %s.",
                interaction.user.id,
            )
            await interaction.followup.send(
                "Não foi possível realizar o saque. Tente novamente.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
