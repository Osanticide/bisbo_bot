import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import os
from utils.interface import Paginator # Sua interface padrão

class SocialShop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self.titles_config = "titles.json"
        
        # Carrega os dados da loja ao iniciar
        self.shop_data = self._carregar_json()

    def _carregar_json(self):
        """Lê os itens da loja do arquivo JSON"""
        if not os.path.exists(self.titles_config):
            return {}
        
        with open(self.titles_config, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Retorna apenas a parte da loja, ou dicionário vazio se não existir
            return data.get("shop_items", {})

    # --- HELPERS DE BANCO DE DADOS ---

    def _get_saldo(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT wallet FROM economia WHERE user_id = ?', (str(user_id),))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else 0

    def _transacao(self, user_id, valor):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE economia SET wallet = wallet + ? WHERE user_id = ?', (valor, str(user_id)))
        conn.commit()
        conn.close()

    def _add_titulo(self, user_id, novo_titulo):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Busca títulos atuais
        cursor.execute('SELECT titulos_desbloqueados FROM social_profiles WHERE user_id = ?', (str(user_id),))
        res = cursor.fetchone()
        
        if not res:
            # Se o usuário não tiver perfil, cria agora
            titulos_atuais = []
            cursor.execute('INSERT INTO social_profiles (user_id) VALUES (?)', (str(user_id),))
        else:
            raw = res[0]
            if raw == "Nenhum" or not raw:
                titulos_atuais = []
            else:
                titulos_atuais = [t.strip() for t in raw.split(',')]

        # Adiciona se não tiver
        if novo_titulo not in titulos_atuais:
            titulos_atuais.append(novo_titulo)
            nova_string = ",".join(titulos_atuais)
            cursor.execute('UPDATE social_profiles SET titulos_desbloqueados = ? WHERE user_id = ?', (nova_string, str(user_id)))
            
        conn.commit()
        conn.close()

    def _tem_titulo(self, user_id, titulo_alvo):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT titulos_desbloqueados FROM social_profiles WHERE user_id = ?', (str(user_id),))
        res = cursor.fetchone()
        conn.close()
        
        if not res or not res[0]: return False
        lista = [t.strip().lower() for t in res[0].split(',')]
        return titulo_alvo.lower() in lista

    # --- FACTORY PARA O PAGINATOR ---
    
    async def _shop_embed_factory(self, page_items, current_page, total_pages):
        """
        Gera o visual da loja. 
        'page_items' será uma lista de tuplas: [('key', {dados}), ('key', {dados})...]
        """
        embed = discord.Embed(
            title="💎 Empório de Títulos de Luxo",
            description="Compre títulos exclusivos para ostentar no seu `/perfil`.\nUse `/comprar_titulo [ID]` para adquirir.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4213/4213641.png") # Ícone genérico de loja chique

        for item_id, dados in page_items:
            nome = dados.get('nome', 'Item Misterioso')
            preco = dados.get('preco', 0)
            desc = dados.get('descricao', 'Sem descrição.')
            
            embed.add_field(
                name=f"🏷️ {nome}",
                value=f"**ID:** `{item_id}`\n💰 **Preço:** {preco:,} CP\n*{desc}*",
                inline=False
            )
        
        embed.set_footer(text=f"Página {current_page + 1} de {total_pages} | Balance suas finanças com sabedoria.")
        return embed, None

    # --- COMANDOS ---

    @app_commands.command(name="loja_titulos", description="Abre o catálogo de títulos compráveis.")
    async def loja_titulos(self, interaction: discord.Interaction):
        # Recarrega o JSON para garantir que itens novos apareçam sem reiniciar
        self.shop_data = self._carregar_json()
        
        if not self.shop_data:
            return await interaction.response.send_message("❌ A loja está vazia no momento (Nenhum item no JSON).", ephemeral=True)

        # Prepara os dados para paginação (Transforma dict em lista de tuplas)
        items_list = list(self.shop_data.items())
        
        # Divide em páginas de 5 itens
        chunk_size = 5
        pages = [items_list[i:i + chunk_size] for i in range(0, len(items_list), chunk_size)]
        
        # Inicia o Paginator da utils.interface
        view = Paginator(interaction, pages, self._shop_embed_factory)
        embed, _ = await self._shop_embed_factory(pages[0], 0, len(pages))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="comprar_titulo", description="Compra um título da loja.")
    @app_commands.describe(id_item="O ID do título (ex: magnata, palhaco)")
    async def comprar_titulo(self, interaction: discord.Interaction, id_item: str):
        await interaction.response.defer(ephemeral=True)
        
        id_item = id_item.lower().strip()
        self.shop_data = self._carregar_json() # Garante dados frescos
        
        # 1. Verifica se item existe
        item = self.shop_data.get(id_item)
        if not item:
            return await interaction.followup.send(f"❌ Item com ID `{id_item}` não encontrado na loja.\nUse `/loja_titulos` para ver os IDs corretos.")
        
        nome_real = item.get('nome', id_item)
        preco = item.get('preco', 999999)
        
        # 2. Verifica se usuário já tem
        if self._tem_titulo(interaction.user.id, nome_real):
            return await interaction.followup.send(f"⚠️ Você já possui o título **{nome_real}**!")
        
        # 3. Verifica saldo
        saldo = self._get_saldo(interaction.user.id)
        if saldo < preco:
            return await interaction.followup.send(f"💸 **Saldo insuficiente!**\nVocê precisa de **{preco:,} CP**, mas só tem **{saldo:,} CP**.")
        
        # 4. Efetua a compra
        try:
            self._transacao(interaction.user.id, -preco) # Tira dinheiro
            self._add_titulo(interaction.user.id, nome_real) # Entrega produto
            
            embed = discord.Embed(title="🛍️ Compra Realizada!", color=discord.Color.green())
            embed.description = f"Você comprou **{nome_real}** por **{preco:,} CP**.\n\nUse `/titulos` para ver e `/equipar_titulo` para usar."
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Erro na compra: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao processar sua compra. O dinheiro não foi descontado.")

async def setup(bot):
    await bot.add_cog(SocialShop(bot))