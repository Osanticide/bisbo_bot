import logging

import discord
from discord import app_commands
from discord.ext import commands

from app.services.economy import format_money
from app.services.rewards import (
    BRASILIA,
    REWARDS,
    RewardError,
    calculate_reward_xp,
    get_next_reward_time,
    get_period_start,
    roll_reward,
)


logger = logging.getLogger(__name__)


class Rewards(commands.Cog):
    """Comandos de recompensas periódicas."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    reward_group = app_commands.Group(
        name="reward",
        description="Consulte e resgate suas recompensas periódicas.",
    )

    @reward_group.command(
        name="info",
        description="Veja as recompensas disponíveis.",
    )
    @app_commands.guild_only()
    async def reward_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎁 Recompensas do Bisbo",
            description=(
                "Resgate recompensas periódicas para ganhar Chess Points (CP) e XP."
            ),
            color=discord.Color.gold(),
        )

        for data in REWARDS.values():
            minimum = data["minimum"]
            maximum = data["maximum"]

            embed.add_field(
                name=data["name"],
                value=(
                    f"💰 **{minimum}–{maximum} CP**\n"
                    "⏳ Disponível novamente no próximo período."
                ),
                inline=False,
            )

        embed.set_footer(text="Bisbo • Sistema de Recompensas")

        await interaction.response.send_message(embed=embed)

    async def _claim(
        self,
        interaction: discord.Interaction,
        reward_type: str,
    ):
        if self.bot.profiles is None:
            await interaction.response.send_message(
                "O sistema de perfis ainda não está disponível.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        now = discord.utils.utcnow().astimezone(BRASILIA)
        period_start = get_period_start(reward_type, now)

        amount = roll_reward(reward_type)
        earned_xp = calculate_reward_xp(amount)

        try:
            result = await self.bot.profiles.claim_reward(
                user_id=interaction.user.id,
                reward_type=reward_type,
                amount=amount,
                earned_xp=earned_xp,
                period_start=period_start,
            )

        except RewardError as error:
            next_reward = get_next_reward_time(reward_type, now)
            timestamp = int(next_reward.timestamp())

            await interaction.followup.send(
                f"❌ {error}\nVocê poderá resgatar novamente <t:{timestamp}:R>.",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Erro ao conceder recompensa %s para o usuário %s.",
                reward_type,
                interaction.user.id,
            )

            await interaction.followup.send(
                "Não foi possível resgatar sua recompensa. Tente novamente mais tarde.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🎉 Recompensa resgatada!",
            description=(
                f"{interaction.user.mention}, você recebeu "
                f"**{format_money(result['amount'])}**!"
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="✨ XP recebido",
            value=f"+{result['earned_xp']} XP",
            inline=True,
        )

        embed.add_field(
            name="📊 Nível atual",
            value=str(result["level"]),
            inline=True,
        )

        embed.add_field(
            name="💰 Carteira",
            value=format_money(result["amount"]),
            inline=True,
        )

        if result["levels_gained"] > 0:
            embed.add_field(
                name="🆙 Subiu de nível!",
                value=f"Você avançou **{result['levels_gained']}** nível(is)!",
                inline=False,
            )

        embed.set_footer(text="Bisbo • Sistema de Recompensas")

        await interaction.followup.send(embed=embed)

    @reward_group.command(
        name="daily",
        description="Resgate sua recompensa diária.",
    )
    @app_commands.guild_only()
    async def daily(self, interaction: discord.Interaction):
        await self._claim(interaction, "daily")

    @reward_group.command(
        name="weekly",
        description="Resgate sua recompensa semanal.",
    )
    @app_commands.guild_only()
    async def weekly(self, interaction: discord.Interaction):
        await self._claim(interaction, "weekly")

    @reward_group.command(
        name="monthly",
        description="Resgate sua recompensa mensal.",
    )
    @app_commands.guild_only()
    async def monthly(self, interaction: discord.Interaction):
        await self._claim(interaction, "monthly")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rewards(bot))
