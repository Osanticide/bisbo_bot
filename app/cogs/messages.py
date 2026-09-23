import discord
from discord.ext import commands


class MessageXP(commands.Cog):
    """Conta mensagens válidas e processa XP de perfil."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        # Não contabiliza comandos tradicionais do Bisbo.
        if message.content.startswith(self.bot.command_prefix):
            return

        # Mensagem sem texto e sem anexos não conta.
        if not message.content.strip() and not message.attachments:
            return

        if self.bot.xp_service is None:
            return

        try:
            result = await self.bot.xp_service.process_message(message.author.id)
        except Exception:
            print(f"[XP] Falha ao processar mensagem de {message.author.id}.")
            return

        if result["levels_gained"] > 0:
            gained = result["levels_gained"]
            level_text = (
                f"subiu **{gained} nível(is)** e chegou ao nível "
                f"**{result['level']}**!"
            )
            await message.channel.send(
                f"🎉 {message.author.mention} {level_text}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageXP(bot))
