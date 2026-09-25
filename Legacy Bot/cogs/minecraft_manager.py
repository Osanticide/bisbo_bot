import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import json
import uuid
import subprocess
import hashlib

class MinecraftManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        # Substitua pelo ID real do seu cargo (Moderador/Staff)
        self.ID_CARGO_STAFF = 123456789012345678 
        self.whitelist_path = "/minecraft/whitelist.json" 
        self._criar_tabela_mine()

    def _criar_tabela_mine(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogadores_mine (
                discord_id TEXT PRIMARY KEY,
                mine_nick TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    # Função de checagem: True se tiver o cargo OU permissão de Gerenciar Servidor
    def tem_permissao_staff():
        def predicate(interaction: discord.Interaction) -> bool:
            # Verifica se o usuário tem o cargo pelo ID
            tem_cargo = any(role.id == 1464302934366879952 for role in interaction.user.roles)
            # Verifica se é admin do servidor
            e_admin = interaction.user.guild_permissions.manage_guild
            return tem_cargo or e_admin
        return app_commands.check(predicate)

    def gerar_uuid_offline(self, nome):
    # O Minecraft usa o hash MD5 do nome "OfflinePlayer:Nick" para gerar o UUID no modo offline
        hash_objeto = hashlib.md5(f"OfflinePlayer:{nome}".encode('utf-8'))
        bytes_hash = bytearray(hash_objeto.digest())
    
    # Ajusta os bits para a versão 3 do UUID (padrão do Minecraft Offline)
        bytes_hash[6] = (bytes_hash[6] & 0x0f) | 0x30
        bytes_hash[8] = (bytes_hash[8] & 0x3f) | 0x80
    
    # Transforma em string no formato 8-4-4-4-12 (formato padrão de UUID)
        hex_str = bytes_hash.hex()
        return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"

    def atualizar_whitelist_mine(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT mine_nick FROM jogadores_mine')
        jogadores = cursor.fetchall()
        conn.close()

        lista_final = [{"uuid": self.gerar_uuid_offline(nick), "name": nick} for (nick,) in jogadores]

        try:
            with open(self.whitelist_path, 'w', encoding='utf-8') as f:
                json.dump(lista_final, f, indent=4)
            return True
        except Exception as e:
            print(f"Erro ao salvar whitelist.json: {e}")
            return False

    # --- COMANDOS USER ---

    @app_commands.command(name="mineadduser", description="Registra um jogador na whitelist")
    @app_commands.describe(membro="Membro do Discord", nick_mine="Nick no Minecraft")
    @tem_permissao_staff()
    async def mineadduser(self, interaction: discord.Interaction, membro: discord.Member, nick_mine: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO jogadores_mine (discord_id, mine_nick) VALUES (?, ?)', (str(membro.id), nick_mine))
            conn.commit()
            if self.atualizar_whitelist_mine():
                embed = discord.Embed(title="🎮 Minecraft: Novo Registro", description=f"{membro.mention} vinculado a **{nick_mine}**.", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("⚠️ Erro ao atualizar `whitelist.json`.", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="mineremoveuser", description="Remove um jogador da whitelist")
    @tem_permissao_staff()
    async def mineremoveuser(self, interaction: discord.Interaction, membro: discord.Member):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT mine_nick FROM jogadores_mine WHERE discord_id = ?', (str(membro.id),))
            resultado = cursor.fetchone()
            if resultado:
                cursor.execute('DELETE FROM jogadores_mine WHERE discord_id = ?', (str(membro.id),))
                conn.commit()
                self.atualizar_whitelist_mine()
                await interaction.response.send_message(f"🗑️ **{resultado[0]}** removido.")
            else:
                await interaction.response.send_message("⚠️ Usuário não encontrado.", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="mineuserls", description="Lista usuários registrados")
    @tem_permissao_staff()
    async def mineuserls(self, interaction: discord.Interaction):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT discord_id, mine_nick FROM jogadores_mine')
            usuarios = cursor.fetchall()
            if not usuarios:
                return await interaction.response.send_message("📭 Nenhum usuário cadastrado.", ephemeral=True)

            lista = "\n".join([f"• <@{d_id}> — **{nick}**" for d_id, nick in usuarios])
            embed = discord.Embed(title="📋 Jogadores Registrados", description=lista, color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
        finally:
            conn.close()

    # --- GESTÃO DE ENERGIA E STATUS ---

    @app_commands.command(name="minestart", description="Liga o servidor")
    @tem_permissao_staff()
    async def minestart(self, interaction: discord.Interaction):
        await interaction.response.defer()
        checar = subprocess.run("screen -ls | grep mine", shell=True, capture_output=True)
        if b"mine" in checar.stdout:
            return await interaction.followup.send("⚠️ O servidor já está online!")

        pasta_server = os.path.dirname(self.whitelist_path)
        comando = f'cd {pasta_server} && screen -dmS mine bash run.sh'
        try:
            subprocess.run(comando, shell=True, check=True)
            await interaction.followup.send("🚀 Comando enviado! O servidor está iniciando.")
        except Exception as e:
            await interaction.followup.send(f"❌ Falha ao iniciar: {e}")

    @app_commands.command(name="minestop", description="Desliga o servidor")
    @tem_permissao_staff()
    async def minestop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            subprocess.run('screen -S mine -X stuff "stop\n"', shell=True, check=True)
            await interaction.followup.send("🛑 Comando `stop` enviado.")
        except:
            await interaction.followup.send("❌ Erro: O servidor está mesmo ligado?")

    @app_commands.command(name="minestatus", description="Verifica o status")
    async def minestatus(self, interaction: discord.Interaction):
        checar = subprocess.run("screen -ls", shell=True, capture_output=True, text=True)
        status = "🟢 Online" if "mine" in checar.stdout else "🔴 Offline"
        color = discord.Color.green() if "mine" in checar.stdout else discord.Color.red()
        embed = discord.Embed(title="📊 Status Minecraft", description=f"Estado: **{status}**", color=color)
        await interaction.response.send_message(embed=embed)

    # Tratamento de erro de permissão unificado
    @mineadduser.error
    @mineremoveuser.error
    @minestart.error
    @minestop.error
    @mineuserls.error
    async def perms_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("🚫 Apenas a Staff pode usar este comando.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MinecraftManager(bot))