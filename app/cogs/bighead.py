import random
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


# Caminho da pasta que contém as imagens do Bighead.
# O caminho é calculado a partir da raiz do projeto,
# independentemente de onde o bot for iniciado.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BIGHEAD_DIR = PROJECT_ROOT / "assets" / "bighead"

# Extensões de imagem aceitas pelo comando.
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}


class Bighead(commands.Cog):
    """Comandos relacionados às imagens Bighead."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="bighead",
        description="Envia uma imagem aleatória do Noronha Biggest Head.",
    )
    async def bighead(self, interaction: discord.Interaction):
        """Seleciona e envia uma imagem aleatória."""

        # Verifica se a pasta existe.
        if not BIGHEAD_DIR.is_dir():
            await interaction.response.send_message(
                "A pasta de imagens do Muranga de nois todos não foi encontrada.",
                ephemeral=True,
            )
            return

        # Busca somente arquivos com extensões aceitas.
        images = [
            file
            for file in BIGHEAD_DIR.iterdir()
            if file.is_file()
            and file.suffix.lower() in IMAGE_EXTENSIONS
        ]

        # Verifica se existem imagens disponíveis.
        if not images:
            await interaction.response.send_message(
                "Ainda não encontrei imagens do cabeção. 😔",
                ephemeral=True,
            )
            return

        # Escolhe uma imagem aleatória.
        selected_image = random.choice(images)

        # Prepara o arquivo para envio ao Discord.
        try:
            image_file = discord.File(
                selected_image,
                filename=selected_image.name,
            )

            await interaction.response.send_message(
                file=image_file,
            )

        except (OSError, discord.HTTPException):
            # Registra o erro no terminal para facilitar o diagnóstico.
            print(
                f"[Bighead] Erro ao enviar a imagem: {selected_image}"
            )

            # Se a interação ainda não foi respondida,
            # envia uma mensagem de erro ao usuário.
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Não consegui enviar a imagem do Cranio de parabólica.",
                    ephemeral=True,
                )


async def setup(bot: commands.Bot):
    """Carrega o Cog do Bighead no bot."""

    await bot.add_cog(Bighead(bot))