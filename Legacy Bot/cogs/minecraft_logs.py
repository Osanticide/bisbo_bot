import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import sqlite3
import random
import json
import subprocess
import re # Importante para ler números no texto

class MinecraftLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self.piadas_path = "piadas.json"
        
        # --- ⚠️ CONFIGURAÇÃO OBRIGATÓRIA ⚠️ ---
        # Você PRECISA alterar isso para o caminho real da sua VPS
        self.log_path = "/home/seu_usuario/caminho/do/server/logs/latest.log" 
        
        # ID do canal onde os avisos de Join/Leave/Morte aparecerão
        self.channel_id = 1234567890 
        # ----------------------------------------
        
        self.online_count = 0
        self.server_starting = True # Evita spam quando o server tá ligando
        
        # Inicia as tarefas
        self.leitor_task = self.bot.loop.create_task(self.iniciar_leitura())
        self.bot.loop.create_task(self.sincronizar_inicial())

    def cog_unload(self):
        self.leitor_task.cancel()

    # --- MÉTODOS DE SINCRONIZAÇÃO ---

    async def sincronizar_inicial(self):
        """Tenta descobrir quantos players tem online assim que o bot liga"""
        await self.bot.wait_until_ready()
        # Verifica se o screen existe
        checar = subprocess.run("screen -ls | grep mine", shell=True, capture_output=True)
        if b"mine" in checar.stdout:
            print("🔄 Server detectado ligado. Solicitando contagem...")
            await self.enviar_comando_console("list")
        else:
            print("⚠️ Server parece desligado (screen não encontrado).")

    async def enviar_comando_console(self, comando):
        """Envia um comando direto para o console do Linux (Screen)"""
        try:
            # Envia o comando para dentro da sessão 'mine'
            subprocess.run(f'screen -S mine -X stuff "{comando}\n"', shell=True)
        except Exception as e:
            print(f"Erro ao enviar comando para o console: {e}")

    # --- LEITURA DO ARQUIVO (CORE) ---

    async def iniciar_leitura(self):
        await self.bot.wait_until_ready()
        print("👀 Iniciando vigilância do log...")
        
        while True:
            if os.path.exists(self.log_path):
                try:
                    # errors='ignore' evita crash se tiver caractere estranho no chat
                    with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                        # Vai para o final do arquivo (ignora histórico antigo)
                        f.seek(0, os.SEEK_END)
                        
                        while True:
                            linha = f.readline()
                            if not linha:
                                await asyncio.sleep(0.1) # Delay curto para não fritar a CPU
                                if not os.path.exists(self.log_path): break # Se o arquivo sumir/rotacionar
                                continue
                            
                            await self.processar_linha(linha)
                            
                except Exception as e:
                    print(f"⚠️ Erro crítico no leitor de logs: {e}")
                    await asyncio.sleep(5) # Espera um pouco antes de tentar reabrir
            else:
                # Se o arquivo não existe (server desligado ou caminho errado)
                # print(f"❌ Arquivo de log não encontrado em: {self.log_path}")
                await asyncio.sleep(10)

    async def processar_linha(self, linha):
        canal = self.bot.get_channel(self.channel_id)
        if not canal: return

        # Limpeza básica da linha
        linha_limpa = linha.strip()

        # 1. Detectar resposta do comando /list (Sincronização)
        # Padrão comum: "There are 2 of a max of 20 players online:..."
        if "players online" in linha_limpa:
            # Regex para pegar o primeiro número (jogadores atuais)
            match = re.search(r"There are (\d+) of a max", linha_limpa)
            if match:
                qtd = int(match.group(1))
                if self.online_count != qtd:
                    print(f"📊 Contador corrigido de {self.online_count} para {qtd}")
                    self.online_count = qtd
                return # Se foi só uma linha de contagem, para por aqui

        # 2. Entrada de Jogador
        if "joined the game" in linha_limpa:
            try:
                # Formato: [HH:MM:SS] [Server thread/INFO]: Nick joined the game
                partes = linha_limpa.split("]: ")
                if len(partes) > 1:
                    nick = partes[1].split(" joined")[0]
                    self.online_count += 1
                    mencao = self.obter_mencao(nick)
                    await canal.send(f"📥 {mencao} entrou no servidor! Online: `{self.online_count}`")
            except Exception as e:
                print(f"Erro ao processar entrada: {e}")

        # 3. Saída de Jogador
        elif "left the game" in linha_limpa:
            try:
                partes = linha_limpa.split("]: ")
                if len(partes) > 1:
                    nick = partes[1].split(" left")[0]
                    self.online_count = max(0, self.online_count - 1)
                    mencao = self.obter_mencao(nick)
                    await canal.send(f"📤 {mencao} saiu do servidor. Online: `{self.online_count}`")
            except Exception as e:
                print(f"Erro ao processar saída: {e}")

        # 4. Detecção de Mortes
        # Filtramos para garantir que é uma mensagem do Server Thread
        elif "Server thread/INFO" in linha_limpa:
            palavras_morte = ["died", "fell", "slain", "burned", "killed", "drowned", "void", "blown up", "shot by", "withered"]
            
            # Verifica se alguma palavra de morte está na linha E se não é mensagem de chat (<Nick>)
            if any(p in linha_limpa for p in palavras_morte) and "<" not in linha_limpa and ">" not in linha_limpa:
                # Evita notificar mortes enquanto o servidor inicializa (villagers morrendo, etc)
                if "Done (" in linha_limpa:
                    self.server_starting = False
                    await self.enviar_comando_console("list") # Sincroniza ao terminar de ligar
                
                if not self.server_starting:
                    await self.tratar_morte(linha_limpa, canal)

    async def tratar_morte(self, linha, canal):
        try:
            # Tenta pegar o nick. Geralmente é a primeira palavra após "]: "
            conteudo = linha.split("]: ")[1]
            nick = conteudo.split(" ")[0]
            mencao = self.obter_mencao(nick)
            
            # Categorias de piada
            categoria = "generico"
            lower_msg = conteudo.lower()
            
            if "fell" in lower_msg or "ground" in lower_msg: categoria = "queda"
            elif "blown" in lower_msg or "explosion" in lower_msg: categoria = "explosao"
            elif "burned" in lower_msg or "fire" in lower_msg or "lava" in lower_msg: categoria = "fogo"
            elif "drowned" in lower_msg: categoria = "afogamento"
            elif "void" in lower_msg: categoria = "void"
            elif "slain" in lower_msg or "zombie" in lower_msg or "skeleton" in lower_msg: categoria = "mobs"
            elif "shot" in lower_msg: categoria = "mobs"

            piada = self.carregar_piada(categoria)
            await canal.send(f"💀 {mencao} {piada}")
        except:
            pass # Falha silenciosa em linhas complexas

    # --- AUXILIARES (BANCO E JSON) ---

    def obter_mencao(self, nick):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT discord_id FROM jogadores_mine WHERE mine_nick = ?', (nick,))
            resultado = cursor.fetchone()
            conn.close()
            return f"<@{resultado[0]}>" if resultado else f"**{nick}**"
        except:
            return f"**{nick}**"

    def carregar_piada(self, categoria):
        try:
            if not os.path.exists(self.piadas_path): return "faleceu."
            with open(self.piadas_path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            opcoes = dados.get(categoria, dados.get("generico", ["morreu."]))
            return random.choice(opcoes)
        except:
            return "foi de base."

    # --- COMANDO SLASH ---

    @app_commands.command(name="minelist", description="Mostra lista de jogadores online")
    async def minelist(self, interaction: discord.Interaction):
        # Verifica screen
        checar = subprocess.run("screen -ls | grep mine", shell=True, capture_output=True)
        if b"mine" not in checar.stdout:
            return await interaction.response.send_message("🔴 O servidor está **Offline**.", ephemeral=True)

        # Força uma sincronização antes de responder
        await self.enviar_comando_console("list")
        
        # Espera um pouquinho (0.2s) para dar tempo do log ser lido e o contador atualizar
        await asyncio.sleep(0.2)
        
        msg = f"Temos **{self.online_count}** aventureiros online."
        if self.online_count == 0:
            msg = "O servidor está ligado, mas **vazio** no momento. 🦗"

        embed = discord.Embed(title="🎮 Status do Servidor", description=msg, color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MinecraftLogs(bot))