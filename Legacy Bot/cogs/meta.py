import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from utils.interface import Paginator # Importando seu paginador

class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = "2.0"
        self.patches_path = "patches.json"

    # --- AUXILIARES DO MENU DE AJUDA ---

    def _get_cog_visuals(self, cog_name):
        """Define a aparência de cada categoria no menu de ajuda"""
        mapa = {
            # Módulos de Economia
            'EconomyCore': {'titulo': '💰 Banco & Economia', 'emoji': '💳', 'cor': discord.Color.green()},
            'EconomyRewards': {'titulo': '🎁 Recompensas Diárias', 'emoji': '📅', 'cor': discord.Color.gold()},
            'EconomyGames': {'titulo': '🎰 Cassino & Jogos', 'emoji': '🎲', 'cor': discord.Color.red()},
            'EconomyJobs': {'titulo': '💼 Mercado de Trabalho', 'emoji': '🔨', 'cor': discord.Color.blue()},
            
            # Módulos do Sistema (Este arquivo e outros)
            'Meta': {'titulo': 'ℹ️ Sistema & Ajuda', 'emoji': '🤖', 'cor': discord.Color.teal()},
            'Minecraft': {'titulo': '🎮 Gestão Minecraft', 'emoji': '⛏️', 'cor': discord.Color.dark_green()},
            'Quotes': {'titulo': '📸 Memórias & Quotes', 'emoji': '🎞️', 'cor': discord.Color.purple()},
            # Adicione aqui o nome da classe de outros módulos se tiver
        }
        # Padrão caso não encontre o nome exato da classe
        return mapa.get(cog_name, {'titulo': cog_name, 'emoji': '📂', 'cor': discord.Color.light_grey()})

    async def _help_embed_factory(self, item, current_page, total_pages):
        """Gera a página do Embed para o Paginator"""
        cog_name, commands_list = item
        visual = self._get_cog_visuals(cog_name)
        
        embed = discord.Embed(
            title=f"{visual['emoji']} {visual['titulo']}",
            description=f"Comandos do módulo **{cog_name}**.",
            color=visual['cor']
        )
        
        # Ordena alfabeticamente
        commands_list.sort(key=lambda x: x.name)

        texto_comandos = ""
        for cmd in commands_list:
            # Pega a descrição automática do código
            desc = cmd.description if cmd.description else "Sem descrição."
            texto_comandos += f"**/{cmd.name}**\n┗ *{desc}*\n\n"
        
        if not texto_comandos:
            texto_comandos = "Nenhum comando disponível aqui."

        embed.description = texto_comandos
        embed.set_footer(text=f"Categoria {current_page + 1} de {total_pages} • Navegue com as setas")
        return embed, None

    # --- COMANDOS DO SISTEMA ---

    @app_commands.command(name="info", description="Saiba mais sobre a origem e motivação da Cindy")
    async def info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Sobre a Cindy",
            description=(
                "A Cindy nasceu da necessidade de uma gestão ágil e integrada para servidores de jogos em VPS Linux. "
                "Sua motivação principal é unir a utilidade técnica (controle de console e logs) com o entretenimento "
                "da comunidade (frases icônicas e monitoramento de eventos).\n\n"
                "**Desenvolvida para ser o braço direito de administradores de servidores**"
            ),
            color=discord.Color.purple()
        )
        embed.add_field(name="🚀 Versão Atual", value=f"`v{self.version}`", inline=True)
        embed.add_field(name="⚙️ Engine", value="Python / Discord.py", inline=True)
        embed.set_footer(text="Cindy Bot - Gestão & Comunidade")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="patch", description="Mostra as novidades das versões")
    @app_commands.describe(versao="Número da versão (ex: 1.0). Deixe vazio para a atual.")
    async def patch(self, interaction: discord.Interaction, versao: str = None):
        if not os.path.exists(self.patches_path):
            return await interaction.response.send_message("❌ Arquivo de patches não encontrado.", ephemeral=True)

        with open(self.patches_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        v_alvo = versao if versao else self.version

        if v_alvo not in dados:
            return await interaction.response.send_message(f"❌ Versão `{v_alvo}` não encontrada no histórico.", ephemeral=True)

        info_v = dados[v_alvo]
        mudancas = "\n".join([f"• {m}" for m in info_v['mudancas']])

        embed = discord.Embed(
            title=f"📜 Notas de Atualização - v{v_alvo}",
            description=f"**Lançamento:** {info_v['data']}\n\n{mudancas}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ajuda", description="Guia dinâmico de todos os comandos organizados por categoria")
    async def ajuda(self, interaction: discord.Interaction):
        """Substitui o antigo help hardcoded por um dinâmico"""
        
        # 1. Varre todos os Cogs carregados no Bot
        lista_de_paginas = []
        for cog_name, cog_instance in self.bot.cogs.items():
            app_cmds = cog_instance.get_app_commands()
            if app_cmds:
                lista_de_paginas.append((cog_name, app_cmds))

        if not lista_de_paginas:
            return await interaction.response.send_message("❌ Nenhum comando encontrado.", ephemeral=True)

        # 2. Ordena para ficar bonito (EconomyCore primeiro, depois o resto ou alfabético)
        lista_de_paginas.sort(key=lambda x: x[0])

        # 3. Chama o Paginator
        view = Paginator(interaction, lista_de_paginas, self._help_embed_factory)
        embed, _ = await self._help_embed_factory(lista_de_paginas[0], 0, len(lista_de_paginas))
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Meta(bot))