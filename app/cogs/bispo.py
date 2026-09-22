import asyncio
import random
from io import BytesIO
from urllib.parse import urlparse

import aiohttp
import discord
from PIL import Image, UnidentifiedImageError
from discord import app_commands
from discord.ext import commands
from ddgs import DDGS


# Configurações do comando
MAX_RESULTS = 30
MAX_ATTEMPTS = 5
MAX_IMAGE_SIZE = 8 * 1024 * 1024  # 8 MB

SEARCH_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 12


# Tipos de imagem aceitos
ALLOWED_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


# Assinaturas para validar o conteúdo real da imagem
IMAGE_SIGNATURES = {
    "jpg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),
}


def is_valid_image(data: bytes, extension: str) -> bool:
    """
    Confere a assinatura e tenta validar a estrutura da imagem
    com Pillow. Também descarta imagens muito pequenas.
    """

    signatures = IMAGE_SIGNATURES.get(extension, ())

    if not any(data.startswith(sig) for sig in signatures):
        return False

    # WEBP precisa ter o identificador WEBP no cabeçalho
    if extension == "webp":
        if len(data) < 12 or data[8:12] != b"WEBP":
            return False

    try:
        # verify() checa a estrutura do arquivo sem decodificar
        # todos os pixels. Reabrimos depois para ler as dimensões.
        with Image.open(BytesIO(data)) as image:
            image.verify()

        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image_format = (image.format or "").upper()

        expected_formats = {
            "jpg": {"JPEG"},
            "png": {"PNG"},
            "gif": {"GIF"},
            "webp": {"WEBP"},
        }

        if image_format not in expected_formats.get(extension, set()):
            return False

        # Evita ícones/miniaturas minúsculos; não exige alta resolução.
        if width < 120 or height < 120:
            return False

        return True

    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return False


def is_valid_url(url: str) -> bool:
    """
    Aceita somente URLs HTTP ou HTTPS.
    """

    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def search_images(query: str) -> list[dict]:
    """
    Executa a busca DDGS fora do event loop do Discord.

    Isso evita bloquear o bot enquanto a pesquisa acontece.
    """

    with DDGS(timeout=SEARCH_TIMEOUT) as ddgs:
        results = ddgs.images(
            query=query,
            region="wt-wt",
            safesearch="moderate",
            max_results=MAX_RESULTS,
        )

        return list(results)


async def download_image(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[bytes, str] | None:
    """
    Baixa e valida uma imagem.

    Retorna os bytes e a extensão quando tudo está correto.
    """

    if not is_valid_url(url):
        return None

    try:
        async with session.get(
            url,
            allow_redirects=True,
        ) as response:

            if response.status != 200:
                return None

            # Verifica o tamanho informado pelo servidor
            content_length = response.headers.get("Content-Length")

            if content_length:
                try:
                    if int(content_length) > MAX_IMAGE_SIZE:
                        return None
                except ValueError:
                    pass

            # Verifica o tipo informado pelo servidor
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";")[0]
                .strip()
                .lower()
            )

            extension = ALLOWED_MIME_TYPES.get(content_type)

            if not extension:
                return None

            # Lê a imagem
            data = await response.content.read(
                MAX_IMAGE_SIZE + 1
            )

            # Impede arquivos maiores que o limite
            if not data or len(data) > MAX_IMAGE_SIZE:
                return None

            # Valida o conteúdo real da imagem
            if not is_valid_image(data, extension):
                return None

            return data, extension

    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ValueError,
    ):
        return None


class Bispo(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="bispo",
        description="Encontra uma imagem aleatória de um bispo de xadrez."
    )
    @app_commands.describe(
        cor="Escolha a etnia do bispo."
    )
    @app_commands.choices(
        cor=[
            app_commands.Choice(
                name="Branca",
                value="white",
            ),
            app_commands.Choice(
                name="Preta",
                value="black",
            ),
        ]
    )
    async def bispo(
        self,
        interaction: discord.Interaction,
        cor: app_commands.Choice[str],
    ):

        await interaction.response.defer()

        # Define a pesquisa de acordo com a cor escolhida
        if cor.value == "white":
            query = "white chess bishop piece"
            cor_nome = "Branca"

        else:
            query = "black chess bishop piece"
            cor_nome = "Preta"

        try:
            # Pesquisa DDGS fora do event loop
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    search_images,
                    query,
                ),
                timeout=SEARCH_TIMEOUT + 5,
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏳ A pesquisa demorou demais. Tente novamente."
            )
            return

        except Exception as error:
            print(f"[BISPO] Erro na pesquisa DDGS: {error}")

            await interaction.followup.send(
                "❌ Não consegui pesquisar imagens agora. "
                "Tente novamente em alguns instantes."
            )
            return

        if not results:
            await interaction.followup.send(
                "🔎 Não encontrei imagens nessa pesquisa."
            )
            return

        # Embaralha os resultados para dar imprevisibilidade
        random.shuffle(results)

        timeout = aiohttp.ClientTimeout(
            total=DOWNLOAD_TIMEOUT
        )

        # Limita conexões simultâneas do comando
        connector = aiohttp.TCPConnector(
            limit=5,
            ssl=True,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "BisboDiscordBot/1.0"
            },
        ) as session:

            attempts = 0

            for result in results:

                if attempts >= MAX_ATTEMPTS:
                    break

                image_url = result.get("image")

                if not image_url:
                    continue

                if not is_valid_url(image_url):
                    continue

                attempts += 1

                downloaded = await download_image(
                    session,
                    image_url,
                )

                if downloaded is None:
                    continue

                image_data, extension = downloaded

                # Nome temporário do arquivo enviado ao Discord
                filename = f"bispo.{extension}"

                image_file = discord.File(
                    BytesIO(image_data),
                    filename=filename,
                )

                # Embed com a imagem
                embed = discord.Embed(
                    title=f"♟ Bispo {cor_nome}",
                    color=discord.Color.from_rgb(
                        230, 230, 230
                    ) if cor.value == "white"
                    else discord.Color.from_rgb(
                        40, 40, 40
                    ),
                )

                embed.set_image(
                    url=f"attachment://{filename}"
                )

                # Link da página de origem, se disponível
                source_url = result.get("url")

                if source_url and is_valid_url(source_url):
                    embed.description = (
                        f"[Ver imagem original]({source_url})"
                    )

                await interaction.followup.send(
                    embed=embed,
                    file=image_file,
                )

                return

        # Nenhuma imagem conseguiu ser baixada
        await interaction.followup.send(
            "⚠️ Encontrei imagens, mas não consegui "
            "baixar nenhuma delas. Tente novamente."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Bispo(bot))