import discord
from discord import app_commands
from discord.ext import commands

from app.services.economy import (
    EconomyError,
    format_money,
    validate_amount,
)


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

            await interaction.response.send_message(embed=embed)

        except Exception:
            print(
                f"[ECONOMY] Erro ao consultar saldo do usuário {interaction.user.id}."
            )

            await interaction.response.send_message(
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
        try:
            amount = validate_amount(valor)

            result = await self.bot.profiles.deposit(
                interaction.user.id,
                amount,
            )

            await interaction.response.send_message(
                f"🏦 Você depositou **{format_money(amount)}**.\n"
                f"👛 Carteira: {format_money(result['wallet'])}\n"
                f"🏦 Banco: {format_money(result['bank'])}"
            )

        except EconomyError as error:
            await interaction.response.send_message(
                str(error),
                ephemeral=True,
            )

        except Exception:
            print(f"[ECONOMY] Erro no depósito do usuário {interaction.user.id}.")

            await interaction.response.send_message(
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
        try:
            amount = validate_amount(valor)

            result = await self.bot.profiles.withdraw(
                interaction.user.id,
                amount,
            )

            await interaction.response.send_message(
                f"💵 Você sacou **{format_money(amount)}**.\n"
                f"👛 Carteira: {format_money(result['wallet'])}\n"
                f"🏦 Banco: {format_money(result['bank'])}"
            )

        except EconomyError as error:
            await interaction.response.send_message(
                str(error),
                ephemeral=True,
            )

        except Exception:
            print(f"[ECONOMY] Erro no saque do usuário {interaction.user.id}.")

            await interaction.response.send_message(
                "Não foi possível realizar o saque. Tente novamente.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
