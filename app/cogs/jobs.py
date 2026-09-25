import discord
from discord import app_commands
from discord.ext import commands

from app.services.jobs import JobCooldownError, JobError


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
            description="Escolha um emprego usando `/job apply <número>`.",
            color=discord.Color.blurple(),
        )

        lines = []

        for index, job in enumerate(jobs, start=1):
            lines.append(f"**{index}.** {job['name']}")

        embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed)

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
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📤 Emprego abandonado",
            description=(f"Você abandonou o emprego de **{result['name']}**."),
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
