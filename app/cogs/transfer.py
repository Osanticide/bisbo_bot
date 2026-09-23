import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from app.services.economy import EconomyError, format_money, validate_amount

logger = logging.getLogger(__name__)
BISBO_USER_ID = 1551612851397988403


class Transfer(commands.Cog):
    """Transferências entre usuários do Bisbo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="transferir", description="Transfira CP para outro usuário.")
    @app_commands.guild_only()
    @app_commands.describe(
        origem="Conta de onde sairá o valor",
        valor="Valor total debitado de você",
        usuario="Destinatário da transferência",
    )
    async def transferir(
        self,
        interaction: discord.Interaction,
        origem: Literal["carteira", "banco"],
        valor: str,
        usuario: discord.Member,
    ):
        await interaction.response.defer(thinking=True)

        try:
            amount = validate_amount(valor)
            result = await self.bot.profiles.transfer(
                sender_id=interaction.user.id,
                recipient_id=usuario.id,
                source=origem,
                amount=amount,
                bisbo_id=BISBO_USER_ID,
            )
            await interaction.followup.send(
                f"✅ Transferência concluída para {usuario.mention}.\n"
                f"💸 Debitado: **{format_money(result['debited'])}**\n"
                f"📥 Destinatário recebeu: **{format_money(result['received'])}**\n"
                f"🏦 Taxa do Bisbo (5%): **{format_money(result['fee'])}**"
            )
        except EconomyError as error:
            await interaction.followup.send(str(error), ephemeral=True)
        except Exception:
            logger.exception("Erro na transferência do usuário %s.", interaction.user.id)
            await interaction.followup.send(
                "Não foi possível realizar a transferência. Tente novamente.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Transfer(bot))
