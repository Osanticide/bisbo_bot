import discord
from discord import app_commands
from discord.ext import commands


def create_xp_bar(current_xp: int, required_xp: int) -> str:
    """Gera uma barra de XP com 10 blocos."""

    if required_xp <= 0:
        progress = 0
    else:
        progress = current_xp / required_xp

    progress = max(0, min(progress, 1))

    filled = int(progress * 10)
    empty = 10 - filled

    return "🟩" * filled + "⬜" * empty


class Profile(commands.Cog):
    """Comandos relacionados aos perfis dos usuários."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="perfil",
        description="Visualize seu perfil ou o de outro membro.",
    )
    @app_commands.guild_only()
    @app_commands.describe(membro="Membro cujo perfil você deseja visualizar.")
    async def perfil(
        self,
        interaction: discord.Interaction,
        membro: discord.Member | None = None,
    ):
        # Se nenhum membro for informado, usa quem executou o comando.
        membro = membro or interaction.user

        # Impede a execução caso o banco não esteja disponível.
        if self.bot.profiles is None:
            await interaction.response.send_message(
                "O sistema de perfis ainda não está disponível.",
                ephemeral=True,
            )
            return

        try:
            profile = await self.bot.profiles.get_or_create_profile(membro.id)
        except Exception:
            print(f"[PROFILE] Erro ao buscar perfil de {membro.id}.")

            await interaction.response.send_message(
                "Não foi possível carregar este perfil. Tente novamente mais tarde.",
                ephemeral=True,
            )
            return

        # Dados de progressão.
        level = profile["level"]
        xp = profile["xp"]
        required_xp = 20 * level

        xp_bar = create_xp_bar(xp, required_xp)

        # Dados econômicos.
        wallet = profile["wallet"]
        bank = profile["bank"]
        net_worth = wallet + bank

        # Dados profissionais.
        profession = profile["profession"]
        profession_level = profile["profession_level"]

        if profession is None:
            profession_text = "Nenhuma profissão"
        else:
            profession_text = f"{profession} — Nível {profession_level}"

        # Criação do embed.
        embed = discord.Embed(
            title=f"Perfil de {membro.display_name}",
            color=discord.Color.blurple(),
        )

        # Identidade.
        embed.set_thumbnail(url=membro.display_avatar.url)

        embed.add_field(
            name="👤 Identidade",
            value=(f"**Usuário:** {membro.mention}\n**Nível:** {level}"),
            inline=False,
        )

        # Progressão.
        embed.add_field(
            name="✨ Experiência",
            value=(
                f"{xp_bar}\n"
                f"**{xp} / {required_xp} XP**\n"
                f"Faltam **{max(0, required_xp - xp)} XP** "
                f"para o próximo nível."
            ),
            inline=False,
        )

        # Economia.
        embed.add_field(
            name="💰 Economia",
            value=(
                f"**Carteira:** {wallet:,}\n"
                f"**Banco:** {bank:,}\n"
                f"**Patrimônio total:** {net_worth:,}"
            ),
            inline=False,
        )

        # Profissão.
        embed.add_field(
            name="💼 Profissão",
            value=profession_text,
            inline=False,
        )

        embed.set_footer(text="Bisbo • Sistema de Perfil")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
