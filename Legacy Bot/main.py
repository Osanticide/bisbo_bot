import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# 1. Carrega variáveis
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 2. Configura Intents
intents = discord.Intents.default()
intents.message_content = True  # Crucial para comandos de texto (prefixo)

# 3. Classe do Bot
class CindyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", # Prefixo para comandos de adm (como !sync)
            intents=intents,
            help_command=None,
            application_id=os.getenv('DISCORD_APP_ID') # Opcional, ajuda no sync mas não é obrigatório
        )

    async def setup_hook(self):
        print("--- 📂 Carregando Módulos (Cogs) ---")
        # Carrega tudo que estiver na pasta 'cogs'
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ {filename} carregado.')
                except Exception as e:
                    print(f'❌ Falha ao carregar {filename}: {e}')
        
        # Sincronização Automática (Útil em desenvolvimento)
        print("--- 🔄 Sincronizando Comandos... ---")
        try:
            synced = await self.tree.sync()
            print(f"✨ Sucesso! {len(synced)} comandos Slash sincronizados.")
        except Exception as e:
            print(f"⚠️ Erro no Sync Automático: {e}")

    async def on_ready(self):
        print(f'--- 🤖 {self.user.name} ONLINE ---')
        print(f'ID: {self.user.id}')
        
        # Define o status do bot ("Jogando /perfil")
        activity = discord.Game(name="/perfil | /roulette_start")
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = CindyBot()

# --- COMANDO DE EMERGÊNCIA (!sync) ---
# Se os comandos Slash pararem de funcionar, digite !sync no chat
@bot.command(name="sync")
async def sync(ctx):
    # Apenas donos/admins deveriam usar, mas para teste deixei aberto
    print("Forçando sincronização manual...")
    msg = await ctx.send("🔄 Sincronizando...")
    try:
        synced = await bot.tree.sync()
        await msg.edit(content=f"✅ Sincronizado! {len(synced)} comandos atualizados.")
    except Exception as e:
        await msg.edit(content=f"❌ Erro ao sincronizar: {e}")

# Inicia
if __name__ == '__main__':
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Erro fatal ao iniciar: {e}")