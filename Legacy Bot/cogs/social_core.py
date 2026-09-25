import discord
from discord.ext import commands, tasks
import sqlite3
import json
import os
import random
from datetime import datetime

# --- CONFIGURAÇÕES DE BALANCEAMENTO ---
XP_POR_MENSAGEM = (15, 25) # Ganha entre 15 e 25 XP
XP_COOLDOWN = 1           # Segundos para ganhar XP de novo (Anti-Spam)
XP_VOICE = 100             # Quanto ganha na call
XP_VOICE_TIMER = 10        # A cada quantos minutos ganha XP na call

class SocialCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self.titles_config = "titles.json"
        
        # Inicia a infraestrutura
        self._criar_tabelas_social()
        self._carregar_titulos()
        
        # Cache de Memória para Cooldown (Mais rápido que banco de dados)
        self.xp_cooldowns = {} 
        
        # Inicia o loop de voz
        self.voice_xp_loop.start()

    def _carregar_titulos(self):
        """Lê o arquivo JSON de configuração"""
        if not os.path.exists(self.titles_config):
            print(f"⚠️ AVISO: {self.titles_config} não encontrado. Criando vazio.")
            with open(self.titles_config, 'w', encoding='utf-8') as f:
                json.dump({"level_rewards": {}, "shop_items": {}}, f, indent=4)
        
        with open(self.titles_config, 'r', encoding='utf-8') as f:
            self.data_config = json.load(f)

    def _criar_tabelas_social(self):
        """Cria a tabela de perfis separada da economia"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_profiles (
                user_id TEXT PRIMARY KEY,
                xp_atual INTEGER DEFAULT 0,
                nivel INTEGER DEFAULT 1,
                bio TEXT DEFAULT 'Um aventureiro em ascensão...',
                titulo_equipado TEXT DEFAULT 'Nenhum',
                titulos_desbloqueados TEXT DEFAULT 'Nenhum',
                cor_tema INTEGER DEFAULT 3447003 -- Azul Discord Padrão
            )
        ''')
        conn.commit()
        conn.close()

    def get_xp_necessario(self, nivel_atual):
        """Curva de dificuldade: Nível * 500 XP"""
        return nivel_atual * 500

    async def processar_xp(self, user: discord.Member, quantidade: int, channel=None):
        """Função central que adiciona XP e verifica Level Up"""
        if user.bot: return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Garante registro
        cursor.execute('INSERT OR IGNORE INTO social_profiles (user_id) VALUES (?)', (str(user.id),))
        
        # Lê dados atuais
        cursor.execute('SELECT xp_atual, nivel, titulos_desbloqueados FROM social_profiles WHERE user_id = ?', (str(user.id),))
        dados = cursor.fetchone()
        
        xp_atual, nivel, titulos_str = dados
        
        novo_xp = xp_atual + quantidade
        xp_prox = self.get_xp_necessario(nivel)
        
        # Lógica de Level Up
        if novo_xp >= xp_prox:
            novo_xp -= xp_prox # Reseta a barra (Estilo RPG)
            nivel += 1
            
            # Verifica se ganhou título novo do JSON
            recompensas = self.data_config.get("level_rewards", {})
            novo_titulo = recompensas.get(str(nivel))
            
            msg_extra = ""
            if novo_titulo:
                lista_titulos = [t.strip() for t in titulos_str.split(',') if t.strip() != "Nenhum"]
                if novo_titulo not in lista_titulos:
                    lista_titulos.append(novo_titulo)
                    titulos_str = ",".join(lista_titulos)
                    msg_extra = f"\n🏆 **Novo Título Desbloqueado:** `{novo_titulo}`"
            
            # Salva Level UP
            cursor.execute('''
                UPDATE social_profiles 
                SET xp_atual = ?, nivel = ?, titulos_desbloqueados = ? 
                WHERE user_id = ?
            ''', (novo_xp, nivel, titulos_str, str(user.id)))
            
            # Notifica no canal (se houver permissão e canal definido)
            if channel:
                try:
                    embed = discord.Embed(title="🆙 LEVEL UP!", color=discord.Color.gold())
                    embed.description = f"Parabéns {user.mention}!\nVocê alcançou o **Nível {nivel}**!{msg_extra}"
                    embed.set_thumbnail(url=user.display_avatar.url)
                    await channel.send(embed=embed)
                except:
                    pass # Sem permissão de enviar mensagem
                
        else:
            # Apenas salva o XP novo
            cursor.execute('UPDATE social_profiles SET xp_atual = ? WHERE user_id = ?', (novo_xp, str(user.id)))
            
        conn.commit()
        conn.close()

    # --- EVENTO: XP POR CHAT ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if not message.guild: return 

        user_id = message.author.id
        agora = datetime.now()

        # Verifica Cooldown na Memória RAM
        if user_id in self.xp_cooldowns:
            tempo_passado = agora - self.xp_cooldowns[user_id]
            if tempo_passado.total_seconds() < XP_COOLDOWN:
                return # Está no cooldown, ignora

        # Aplica XP
        self.xp_cooldowns[user_id] = agora
        xp_ganho = random.randint(*XP_POR_MENSAGEM)
        
        # Passamos o canal para ele avisar se upar de nível
        await self.processar_xp(message.author, xp_ganho, message.channel)

    # --- TAREFA: XP POR VOZ ---
    @tasks.loop(minutes=XP_VOICE_TIMER)
    async def voice_xp_loop(self):
        """Roda a cada X minutos checando quem está em call"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.voice and member.voice.channel:
                    # Não ganha XP se estiver mutado (evita farm AFK mutado)
                    if not member.bot and not member.voice.self_mute and not member.voice.deaf:
                        # channel=None pois não queremos spammar aviso de level up no chat geral aleatoriamente
                        await self.processar_xp(member, XP_VOICE, channel=None)

async def setup(bot):
    await bot.add_cog(SocialCore(bot))