import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import random
from datetime import datetime
from utils.interface import Paginator 

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self.images_path = "images/quotes"
        self.ultima_frase_id = -1
        self.ultima_imagem = ""
        self._criar_tabela_quotes()

    def _criar_tabela_quotes(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                autor_id TEXT NOT NULL,
                frase TEXT NOT NULL,
                registrado_por TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    # --- FÁBRICAS DE EMBEDS ---

    async def _frase_embed_factory(self, frase, atual, total):
        embed = discord.Embed(title="📜 Arquivo de Frases", color=discord.Color.blue())
        embed.description = f"### \"{frase[2]}\"\n\n**Autor:** <@{frase[1]}>\n**Data:** {frase[3]}"
        embed.set_footer(text=f"Frase {atual + 1} de {total}")
        return embed, None

    async def _imagem_embed_factory(self, nome_arquivo, atual, total):
        caminho = os.path.join(self.images_path, nome_arquivo)
        file = discord.File(caminho, filename="img.png")
        embed = discord.Embed(title="🖼️ Galeria de Imagens", color=discord.Color.blue())
        embed.set_image(url="attachment://img.png")
        embed.set_footer(text=f"Imagem {atual + 1} de {total}")
        return embed, file

    # --- COMANDOS ATUALIZADOS COM DEFER ---

    @app_commands.command(name="quotes_all", description="Lista todas as frases registradas")
    async def quotes_all(self, interaction: discord.Interaction):
        # Avisa ao Discord para esperar o processamento do banco
        await interaction.response.defer()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, autor_id, frase, data FROM quotes')
        frases = cursor.fetchall()
        conn.close()

        if not frases:
            return await interaction.followup.send("📭 Nenhuma frase encontrada.", ephemeral=True)

        view = Paginator(interaction, frases, self._frase_embed_factory)
        embed, _ = await self._frase_embed_factory(frases[0], 0, len(frases))
        
        # Como usamos defer, respondemos com followup
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="images_all", description="Lista todas as imagens da galeria")
    async def images_all(self, interaction: discord.Interaction):
        # Avisa ao Discord para esperar o carregamento das imagens na VPS
        await interaction.response.defer()

        if not os.path.exists(self.images_path):
            return await interaction.followup.send("❌ Pasta de imagens não encontrada.", ephemeral=True)

        arquivos = [f for f in os.listdir(self.images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not arquivos:
            return await interaction.followup.send("🖼️ Galeria de imagens está vazia.", ephemeral=True)

        view = Paginator(interaction, arquivos, self._imagem_embed_factory)
        embed, file = await self._imagem_embed_factory(arquivos[0], 0, len(arquivos))
        
        # Enviamos o arquivo e o embed via followup
        await interaction.followup.send(file=file, embed=embed, view=view)

    # --- COMANDOS RESTANTES (SEM ALTERAÇÃO) ---

    @app_commands.command(name="quote_add", description="Adiciona uma nova frase")
    @app_commands.describe(membro="Quem disse", frase="O que disse")
    async def quote_add(self, interaction: discord.Interaction, membro: discord.Member, frase: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%d/%m/%Y")
        cursor.execute('INSERT INTO quotes (autor_id, frase, registrado_por, data) VALUES (?, ?, ?, ?)',
                       (str(membro.id), frase, str(interaction.user.id), data_atual))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Guardada!", ephemeral=True)

    @app_commands.command(name="quote", description="Sorteia frase e imagem")
    async def quote(self, interaction: discord.Interaction):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, autor_id, frase, data FROM quotes')
        todas = cursor.fetchall()
        if not todas:
            await interaction.response.send_message("Banco vazio.", ephemeral=True)
            conn.close()
            return
        
        escolha_frase = random.choice([f for f in todas if f[0] != self.ultima_frase_id] or todas)
        self.ultima_frase_id = escolha_frase[0]
        conn.close()

        arquivos = [f for f in os.listdir(self.images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if not arquivos:
            return await interaction.response.send_message("Sem imagens.", ephemeral=True)

        escolha_img = random.choice([img for img in arquivos if img != self.ultima_imagem] or arquivos)
        self.ultima_imagem = escolha_img

        id_autor = int(escolha_frase[1])
        try:
            membro = interaction.guild.get_member(id_autor) or await interaction.guild.fetch_member(id_autor)
            nome_autor = membro.display_name
        except:
            nome_autor = "Antigo Membro"

        file = discord.File(os.path.join(self.images_path, escolha_img), filename=escolha_img)
        embed = discord.Embed(description=f'### "{escolha_frase[2]}"', color=discord.Color.random())
        embed.set_author(name=nome_autor)
        embed.set_footer(text=f"Registrado em: {escolha_frase[3]}")
        embed.set_image(url=f"attachment://{escolha_img}")
        await interaction.response.send_message(file=file, embed=embed)

async def setup(bot):
    await bot.add_cog(Quotes(bot))