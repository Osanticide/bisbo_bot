import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
from datetime import datetime, timedelta

class EconomyRewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self._criar_tabelas()

    def _criar_tabelas(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Tabela para gerir os tempos de espera (Cooldowns)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id TEXT,
                comando TEXT,
                ultimo_uso TEXT,
                PRIMARY KEY (user_id, comando)
            )
        ''')
        conn.commit()
        conn.close()

    # --- MÉTODOS AUXILIARES ---

    def _verificar_cooldown(self, user_id, comando, horas_espera):
        """
        Verifica se o utilizador pode usar o comando.
        Retorna: (PodeUsar: bool, TempoRestante: str)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ultimo_uso FROM cooldowns WHERE user_id = ? AND comando = ?', (str(user_id), comando))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return True, None

        ultimo_uso = datetime.fromisoformat(resultado[0])
        agora = datetime.now()
        tempo_passado = agora - ultimo_uso
        tempo_necessario = timedelta(hours=horas_espera)

        if tempo_passado < tempo_necessario:
            restante = tempo_necessario - tempo_passado
            horas, resto = divmod(int(restante.total_seconds()), 3600)
            minutos, _ = divmod(resto, 60)
            return False, f"{horas}h {minutos}m"
        
        return True, None

    def _registar_uso(self, user_id, comando):
        """Atualiza a data do último uso"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        agora = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO cooldowns (user_id, comando, ultimo_uso) 
            VALUES (?, ?, ?)
        ''', (str(user_id), comando, agora))
        conn.commit()
        conn.close()

    def _adicionar_dinheiro(self, user_id, valor):
        """Adiciona dinheiro diretamente à carteira (Wallet)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Garante que a conta existe antes de dar dinheiro
        cursor.execute('INSERT OR IGNORE INTO economia (user_id, wallet, bank) VALUES (?, 0, 0)', (str(user_id),))
        cursor.execute('UPDATE economia SET wallet = wallet + ? WHERE user_id = ?', (valor, str(user_id)))
        conn.commit()
        conn.close()

    # --- LÓGICA DE PROBABILIDADE (RNG) ---

    def _sortear_recompensa(self, tipo="daily"):
        """Define os valores e probabilidades"""
        if tipo == "daily":
            # [Valor, Peso(Chance), Título, Cor]
            tabela = [
                (50, 60, "Comum", discord.Color.light_grey()),
                (100, 30, "Incomum", discord.Color.blue()),
                (300, 9, "Raro", discord.Color.purple()),
                (1000, 1, "LENDÁRIO", discord.Color.gold())
            ]
        elif tipo == "weekly":
            tabela = [
                (500, 50, "Comum", discord.Color.light_grey()),
                (1000, 35, "Incomum", discord.Color.blue()),
                (2500, 14, "Raro", discord.Color.purple()),
                (10000, 1, "MÍTICO", discord.Color.teal())
            ]
        
        # random.choices retorna uma lista baseada nos pesos
        valores, pesos, titulos, cores = zip(*tabela)
        escolha = random.choices(tabela, weights=pesos, k=1)[0]
        return escolha # Retorna a tupla (valor, peso, titulo, cor)

    # --- COMANDOS ---

    @app_commands.command(name="daily", description="Recebe a tua recompensa diária (Aleatória)")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # 1. Verifica Cooldown (24 Horas)
        pode_usar, tempo_restante = self._verificar_cooldown(user_id, "daily", 24)
        
        # MANTÉM PRIVADO: Se der erro de tempo, só o usuário vê
        if not pode_usar:
            return await interaction.response.send_message(
                f"⏳ {interaction.user.mention}, calma lá! Já recebeste o teu daily.\nVolta daqui a **{tempo_restante}**.", 
                ephemeral=True
            )

        # 2. Sorteia o valor
        valor, _, titulo, cor = self._sortear_recompensa("daily")

        # 3. Entrega o dinheiro e regista o uso
        self._adicionar_dinheiro(user_id, valor)
        self._registar_uso(user_id, "daily")

        # 4. Resposta visual PÚBLICA
        embed = discord.Embed(title="📅 Recompensa Diária", color=cor)
        embed.description = f"{interaction.user.mention} abriu o presente diário e tirou um prémio **{titulo}**!"
        embed.add_field(name="Ganhou", value=f"💰 **{valor} CP**")
        embed.set_thumbnail(url=interaction.user.display_avatar.url) # Adiciona a foto do usuário
        embed.set_footer(text="Volta amanhã para mais!")
        
        # Sem ephemeral=True, todos no chat verão
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="weekly", description="Recebe a tua mesada semanal (Prémios Maiores)")
    async def weekly(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # 1. Verifica Cooldown (168 Horas = 7 Dias)
        pode_usar, tempo_restante = self._verificar_cooldown(user_id, "weekly", 168)
        
        # MANTÉM PRIVADO: Erro de tempo
        if not pode_usar:
            return await interaction.response.send_message(
                f"⏳ {interaction.user.mention}, ainda não é dia de pagamento!\nVolta daqui a **{tempo_restante}**.", 
                ephemeral=True
            )

        valor, _, titulo, cor = self._sortear_recompensa("weekly")

        self._adicionar_dinheiro(user_id, valor)
        self._registar_uso(user_id, "weekly")

        # Resposta visual PÚBLICA
        embed = discord.Embed(title="📆 Bónus Semanal", color=cor)
        embed.description = f"Parabéns {interaction.user.mention}! O teu bónus **{titulo}** chegou."
        embed.add_field(name="Recebeu", value=f"💸 **{valor} CP**")
        embed.set_thumbnail(url=interaction.user.display_avatar.url) # Adiciona a foto do usuário
        
        # Sem ephemeral=True, todos no chat verão
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyRewards(bot))