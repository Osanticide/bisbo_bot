import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import traceback # Para ver o erro detalhado no terminal

class SocialProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"

    def get_xp_necessario(self, nivel_atual):
        return nivel_atual * 500

    # --- NOVO: AUTOCOMPLETE ---
    async def titulo_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Sugere apenas os títulos que o usuário POSSUI"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT titulos_desbloqueados FROM social_profiles WHERE user_id = ?', (str(interaction.user.id),))
            result = cursor.fetchone()
            conn.close()

            if not result or not result[0]:
                return []

            # Limpa a lista e remove 'Nenhum'
            lista_bruta = result[0].split(',')
            meus_titulos = [t.strip() for t in lista_bruta if t.strip() and t.strip() != "Nenhum"]

            choices = []
            for titulo in meus_titulos:
                # Filtra conforme o usuário digita (busca parcial)
                if current.lower() in titulo.lower():
                    choices.append(app_commands.Choice(name=titulo, value=titulo))
            
            # O Discord aceita no máx 25 sugestões
            return choices[:25]
            
        except Exception as e:
            print(f"Erro no autocomplete: {e}")
            return []

    # --- COMANDOS ---

    @app_commands.command(name="perfil", description="Exibe seu cartão de perfil com Nível, XP e Economia.")
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None):
        # 1. DEFER (Obrigatório para evitar timeout)
        await interaction.response.defer(ephemeral=False)
        
        try:
            print("--- [DEBUG] Iniciando comando /perfil ---")
            target = usuario or interaction.user
            print(f"--- [DEBUG] Alvo: {target.name} (ID: {target.id}) ---")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            print("--- [DEBUG] Banco de Dados conectado ---")
            
            # 2. Busca dados Sociais
            cursor.execute('''
                SELECT xp_atual, nivel, bio, titulo_equipado, cor_tema 
                FROM social_profiles WHERE user_id = ?
            ''', (str(target.id),))
            social = cursor.fetchone()
            print(f"--- [DEBUG] Dados Sociais: {social} ---")
            
            if not social:
                social = (0, 1, 'Um aventureiro misterioso...', 'Nenhum', 0x3498db) 
            
            xp, nivel, bio, titulo, cor_int = social
            
            # 3. Busca dados de Economia
            cursor.execute('SELECT wallet, banco FROM economia WHERE user_id = ?', (str(target.id),))
            economy = cursor.fetchone()
            saldo_total = (economy[0] + economy[1]) if economy else 0
            print(f"--- [DEBUG] Economia: {saldo_total} ---")
            
            # 4. Busca dados de Trabalho
            cursor.execute('SELECT job_name FROM jobs WHERE user_id = ?', (str(target.id),))
            job = cursor.fetchone()
            trabalho = job[0] if job else "Desempregado"
            print(f"--- [DEBUG] Trabalho: {trabalho} ---")
            
            conn.close()
            
            # --- CÁLCULOS ---
            xp_prox_nivel = self.get_xp_necessario(nivel)
            if xp_prox_nivel <= 0: xp_prox_nivel = 500 # Proteção contra div/0
            
            porcentagem = xp / xp_prox_nivel
            porcentagem_texto = int(porcentagem * 100)
            
            blocos_cheios = int(porcentagem * 10)
            blocos_cheios = max(0, min(10, blocos_cheios)) # Garante entre 0 e 10
            blocos_vazios = 10 - blocos_cheios
            barra = "▰" * blocos_cheios + "▱" * blocos_vazios
            
            print("--- [DEBUG] Cálculos finalizados, montando Embed ---")

            # --- EMBED ---
            # Garante que a cor é válida
            if not isinstance(cor_int, int): cor_int = 0x3498db
            
            embed = discord.Embed(title=f"👤 {target.display_name}", color=discord.Color(cor_int))
            
            descricao = ""
            if titulo and titulo != "Nenhum":
                descricao += f"**🎖️ {titulo}**\n"
            descricao += f"*{bio}*"
            embed.description = descricao

            if target.avatar:
                embed.set_thumbnail(url=target.avatar.url)
            elif target.display_avatar:
                embed.set_thumbnail(url=target.display_avatar.url)
            
            embed.add_field(name=f"⭐ Nível {nivel}", value=f"`{barra}` **{porcentagem_texto}%**\nXP: {xp}/{xp_prox_nivel}", inline=True)
            embed.add_field(name="💰 Fortuna", value=f"**{saldo_total:,} CP**".replace(",", "."), inline=True)
            embed.add_field(name="💼 Ocupação", value=f"{trabalho}", inline=False)
            
            print("--- [DEBUG] Enviando Embed... ---")
            await interaction.followup.send(embed=embed)
            print("--- [DEBUG] Sucesso! ---")

        except Exception as e:
            # SE DEU ERRO, VAI CAIR AQUI
            traceback.print_exc() # Imprime o erro completo no terminal
            err_msg = f"❌ **Erro Crítico:** `{e}`"
            await interaction.followup.send(err_msg)

    @app_commands.command(name="bio", description="Altera a frase do seu perfil.")
    async def bio(self, interaction: discord.Interaction, texto: str):
        await interaction.response.defer(ephemeral=True)
        try:
            if len(texto) > 100:
                return await interaction.followup.send("❌ A bio é muito longa! Use no máximo 100 caracteres.")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO social_profiles (user_id) VALUES (?)', (str(interaction.user.id),))
            cursor.execute('UPDATE social_profiles SET bio = ? WHERE user_id = ?', (texto, str(interaction.user.id)))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"✅ Bio atualizada:\n*{texto}*")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao salvar bio: {e}")

    @app_commands.command(name="titulos", description="Vê seus títulos desbloqueados.")
    async def titulos(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT titulos_desbloqueados, titulo_equipado FROM social_profiles WHERE user_id = ?', (str(interaction.user.id),))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return await interaction.followup.send("Você ainda não tem perfil social.")
                
            lista_str, equipado = result
            if not lista_str: lista_str = "Nenhum"
            
            lista_titulos = [t.strip() for t in lista_str.split(',') if t.strip() != "Nenhum"]
            
            if not lista_titulos:
                return await interaction.followup.send("❌ Você ainda não tem títulos.")
                
            texto_final = f"**Título Atual:** `{equipado}`\n\n**📜 Seus Títulos:**\n"
            for t in lista_titulos:
                if t == equipado:
                    texto_final += f"✅ **{t}** (Equipado)\n"
                else:
                    texto_final += f"🔹 {t}\n"
            
            texto_final += "\nUse `/equipar_titulo` e selecione na lista."
            
            embed = discord.Embed(title="🏆 Galeria de Títulos", description=texto_final, color=discord.Color.gold())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar títulos: {e}")

    @app_commands.command(name="equipar_titulo", description="Equipa um título.")
    @app_commands.describe(nome="Selecione o título da lista")
    @app_commands.autocomplete(nome=titulo_autocomplete) # <--- AQUI ESTÁ A ATUALIZAÇÃO
    async def equipar_titulo(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer(ephemeral=True)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT titulos_desbloqueados FROM social_profiles WHERE user_id = ?', (str(interaction.user.id),))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return await interaction.followup.send("Perfil não encontrado.")
                
            lista_str = result[0]
            if not lista_str: lista_str = ""
            
            lista_titulos = [t.strip() for t in lista_str.split(',')]
            lista_lower = [t.lower() for t in lista_titulos]
            
            if nome.strip().lower() not in lista_lower:
                conn.close()
                return await interaction.followup.send(f"❌ Você não possui o título `{nome}`.\nTente selecionar uma das opções da lista.")
            
            index = lista_lower.index(nome.strip().lower())
            nome_correto = lista_titulos[index]
            
            cursor.execute('UPDATE social_profiles SET titulo_equipado = ? WHERE user_id = ?', (nome_correto, str(interaction.user.id)))
            conn.commit()
            conn.close()
            
            await interaction.followup.send(f"✅ Título atualizado para: **{nome_correto}**")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao equipar: {e}")

async def setup(bot):
    await bot.add_cog(SocialProfile(bot))