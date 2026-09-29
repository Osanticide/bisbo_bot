import discord
from discord import app_commands
from discord.ext import commands

from app.services.jobs import (
    BASE_CP,
    LEVEL_MULTIPLIER,
    MILESTONE_MULTIPLIER,
    PROFILE_XP_RATE,
    PROFESSIONAL_XP_RATE,
    WORK_COOLDOWN,
    JobCooldownError,
    JobError,
    calculate_base_job_cp,
    calculate_work_cp,
    xp_required_for_level,
)
from app.ui import Paginator


class Jobs(commands.Cog):
    """Comandos do sistema de empregos."""

    def __init__(self, bot):
        self.bot = bot

    job = app_commands.Group(
        name="job",
        description="Sistema de empregos.",
    )

    @job.command(
        name="list",
        description="Lista os empregos disponíveis.",
    )
    async def job_list(self, interaction: discord.Interaction):
        jobs = await self.bot.jobs.list_jobs()

        if not jobs:
            await interaction.response.send_message(
                "Não existem empregos disponíveis no momento.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="💼 Empregos disponíveis",
            description=(
                "Escolha um emprego usando `/job apply <número>`.\n"
                "Os valores abaixo representam o pagamento no nível 1."
            ),
            color=discord.Color.blurple(),
        )

        for index, job in enumerate(jobs, start=1):
            coefficient = job["coefficient"]
            base_cp = calculate_base_job_cp(coefficient)

            embed.add_field(
                name=f"{index}. {job['name']}",
                value=(
                    f"💰 Base: **{BASE_CP:.0f} CP**\n"
                    f"📈 Coeficiente: **{coefficient:.2f}x**\n"
                    f"💵 CP no nível 1: **{base_cp:.2f} CP**"
                ),
                inline=False,
            )

        embed.add_field(
            name="📊 Regras de progressão",
            value=(
                f"• XP profissional: **{PROFESSIONAL_XP_RATE * 100:.0f}%** do CP recebido\n"
                f"• XP de perfil: **{PROFILE_XP_RATE * 100:.0f}%** do CP recebido\n"
                f"• Multiplicador por nível: **{LEVEL_MULTIPLIER:.2f}x**\n"
                f"• Marco a cada 5 níveis: **{MILESTONE_MULTIPLIER:.2f}x**"
            ),
            inline=False,
        )

        embed.set_footer(
            text="Use /job info para entender como os valores são calculados."
        )

        await interaction.response.send_message(embed=embed)

    @job.command(
        name="info",
        description="Explica como funciona o sistema de empregos.",
    )
    async def job_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Como funciona o sistema de empregos",
            description=(
                "Trabalhe, evolua sua profissão e aumente seus ganhos "
                "conforme seu nível profissional."
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="💰 Como o CP é calculado",
            value=(
                "O pagamento de cada trabalho começa com uma base de "
                f"**{BASE_CP:.0f} CP** e é afetado pelo coeficiente do emprego.\n\n"
                "A fórmula é:\n"
                "```"
                "CP = 1200 × coeficiente × 1,15^(nível - 1)\n"
                "     × 1,25^floor((nível - 1) / 5)"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="📈 Evolução do pagamento",
            value=(
                f"Cada nível profissional aumenta o pagamento pelo "
                f"multiplicador **{LEVEL_MULTIPLIER:.2f}x**.\n\n"
                f"A cada 5 níveis existe um marco adicional de "
                f"**{MILESTONE_MULTIPLIER:.2f}x**. "
                "Isso faz com que a progressão acelere conforme você evolui."
            ),
            inline=False,
        )

        embed.add_field(
            name="🧑‍💼 XP profissional",
            value=(
                f"Você recebe **{PROFESSIONAL_XP_RATE * 100:.0f}%** do CP ganho "
                "como XP profissional.\n\n"
                "O XP profissional é usado exclusivamente para evoluir "
                "o nível da profissão."
            ),
            inline=True,
        )

        embed.add_field(
            name="⭐ XP de perfil",
            value=(
                f"Você recebe **{PROFILE_XP_RATE * 100:.0f}%** do CP ganho "
                "como XP de perfil.\n\n"
                "Esse XP contribui para a evolução geral do seu perfil."
            ),
            inline=True,
        )

        embed.add_field(
            name="🆙 Nível profissional",
            value=(
                "O XP necessário aumenta conforme seu nível.\n\n"
                "**XP necessário = 1000 × nível atual**\n\n"
                "Exemplo:\n"
                "Nível 1 → 1.000 XP\n"
                "Nível 2 → 2.000 XP\n"
                "Nível 3 → 3.000 XP"
            ),
            inline=False,
        )

        embed.add_field(
            name="⏱️ Cooldown de trabalho",
            value=(
                "Depois de trabalhar, você precisa esperar "
                "**4 horas** para trabalhar novamente."
            ),
            inline=True,
        )

        embed.add_field(
            name="📤 Abandono do emprego",
            value=(
                "Depois de ser contratado, é necessário permanecer "
                "**24 horas** no emprego antes de poder abandoná-lo.\n\n"
                "Abandonar um emprego não apaga seu progresso profissional."
            ),
            inline=True,
        )

        embed.set_footer(text="Use /job list para ver os empregos disponíveis.")

        await interaction.response.send_message(embed=embed)

    @job.command(
        name="carteira",
        description="Consulta seu contrato e histórico de empregos.",
    )
    async def job_carteira(self, interaction: discord.Interaction):
        history = await self.bot.jobs.get_job_history(interaction.user.id)

        if not history:
            await interaction.response.send_message(
                "📭 Você ainda não possui nenhum contrato de emprego.",
                ephemeral=True,
            )
            return

        async def build_embed(contract, page, total):
            is_current = contract["is_current"]

            status = "🟢 Contrato atual" if is_current else "📁 Contrato encerrado"

            title = "💼 Carteira profissional"

            if page > 0:
                title = "📁 Histórico profissional"

            embed = discord.Embed(
                title=title,
                color=(
                    discord.Color.green() if is_current else discord.Color.blurple()
                ),
            )

            embed.add_field(
                name="Emprego",
                value=f"**{contract['name']}**",
                inline=False,
            )

            embed.add_field(
                name="Status",
                value=status,
                inline=True,
            )

            embed.add_field(
                name="Coeficiente",
                value=f"**{contract['coefficient']:.2f}x**",
                inline=True,
            )

            hired_at = int(contract["hired_at"].timestamp())

            embed.add_field(
                name="Contratado em",
                value=f"<t:{hired_at}:F>",
                inline=False,
            )

            if contract["abandoned_at"] is not None:
                abandoned_at = int(contract["abandoned_at"].timestamp())

                embed.add_field(
                    name="Encerrado em",
                    value=f"<t:{abandoned_at}:F>",
                    inline=False,
                )

            if is_current:
                level = contract["level"] or 1
                xp = contract["xp"] or 0
                xp_required = xp_required_for_level(level)

                work_cp = calculate_work_cp(
                    contract["coefficient"],
                    level,
                )

                embed.add_field(
                    name="Nível profissional",
                    value=f"**{level}**",
                    inline=True,
                )

                embed.add_field(
                    name="XP profissional",
                    value=f"**{xp:,} / {xp_required:,} XP**",
                    inline=True,
                )

                embed.add_field(
                    name="Pagamento atual",
                    value=f"**{work_cp:.2f} CP** por trabalho",
                    inline=False,
                )

                last_work_at = contract["last_work_at"]

                if last_work_at is not None:
                    next_work_at = last_work_at + WORK_COOLDOWN
                    next_timestamp = int(next_work_at.timestamp())

                    embed.add_field(
                        name="Próximo trabalho",
                        value=f"<t:{next_timestamp}:R>",
                        inline=True,
                    )

            if total > 1:
                embed.set_footer(
                    text=(
                        f"Contrato {page + 1} de {total} • "
                        "⬅️ mais recente • ➡️ mais antigo"
                    )
                )
            else:
                embed.set_footer(text="Seu histórico possui 1 contrato.")

            return embed

        view = Paginator(
            interaction,
            history,
            build_embed,
        )

        embed, file = await view.build_page()

        if file is not None:
            await interaction.response.send_message(
                embed=embed,
                file=file,
                view=view,
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=view,
            )

        view.message = await interaction.original_response()

    @job.command(
        name="apply",
        description="Candidate-se a um emprego.",
    )
    @app_commands.describe(
        numero="Número do emprego exibido em /job list.",
    )
    async def job_apply(
        self,
        interaction: discord.Interaction,
        numero: app_commands.Range[int, 1, 100],
    ):
        try:
            result = await self.bot.jobs.apply_job(
                interaction.user.id,
                numero,
            )

        except JobError as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="💼 Emprego contratado",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Emprego",
            value=result["name"],
            inline=False,
        )

        embed.add_field(
            name="Nível profissional",
            value=str(result["level"]),
            inline=True,
        )

        embed.add_field(
            name="XP profissional",
            value=str(result["xp"]),
            inline=True,
        )

        embed.set_footer(text="Você poderá abandonar este emprego após 24 horas.")

        await interaction.response.send_message(embed=embed)

    @job.command(
        name="abandon",
        description="Abandona seu emprego atual.",
    )
    async def job_abandon(self, interaction: discord.Interaction):
        try:
            result = await self.bot.jobs.abandon_job(interaction.user.id)

        except JobError as error:
            message = f"❌ {error}"

            if interaction.response.is_done():
                await interaction.followup.send(
                    message,
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
            return

        embed = discord.Embed(
            title="📤 Emprego abandonado",
            description=f"Você abandonou o emprego de **{result['name']}**.",
            color=discord.Color.orange(),
        )

        embed.set_footer(text="Seu progresso profissional foi preservado.")

        await interaction.response.send_message(embed=embed)

    @job.command(
        name="work",
        description="Trabalha no seu emprego atual.",
    )
    async def job_work(self, interaction: discord.Interaction):
        try:
            result = await self.bot.jobs.work(interaction.user.id)

        except JobCooldownError as error:
            timestamp = int(error.retry_at.timestamp())

            await interaction.response.send_message(
                (
                    "⏳ Você ainda está no cooldown.\n"
                    f"Você poderá trabalhar novamente "
                    f"<t:{timestamp}:R>."
                ),
                ephemeral=True,
            )
            return

        except JobError as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="💼 Trabalho concluído",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Emprego",
            value=result["job_name"],
            inline=False,
        )

        embed.add_field(
            name="CP recebido",
            value=f"{result['cp']:.2f} CP",
            inline=True,
        )

        embed.add_field(
            name="XP profissional",
            value=f"+{result['professional_xp']} XP",
            inline=True,
        )

        embed.add_field(
            name="XP de perfil",
            value=f"+{result['profile_xp']} XP",
            inline=True,
        )

        embed.add_field(
            name="Nível profissional",
            value=str(result["job_level"]),
            inline=True,
        )

        if result["job_levels_gained"] > 0:
            embed.add_field(
                name="🎉 Evolução profissional",
                value=(
                    f"+{result['job_levels_gained']} nível"
                    f"{'s' if result['job_levels_gained'] != 1 else ''}"
                ),
                inline=False,
            )

        if result["profile_levels_gained"] > 0:
            embed.add_field(
                name="⭐ Evolução de perfil",
                value=(
                    f"+{result['profile_levels_gained']} nível"
                    f"{'s' if result['profile_levels_gained'] != 1 else ''}"
                ),
                inline=False,
            )

        next_timestamp = int(result["next_work_at"].timestamp())

        embed.set_footer(text="Próximo trabalho disponível")
        embed.description = f"Você poderá trabalhar novamente <t:{next_timestamp}:R>."

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Jobs(bot))
