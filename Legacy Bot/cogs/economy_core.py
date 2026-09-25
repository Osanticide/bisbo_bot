import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

class EconomyCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self._criar_tabela_economia()

    def _criar_tabela_economia(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS economia (
                user_id TEXT PRIMARY KEY,
                wallet INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    # --- MÉTODOS INTERNOS ---

    def _ensure_account(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO economia (user_id, wallet, bank) VALUES (?, 0, 0)', (str(user_id),))
        conn.commit()
        conn.close()

    def _get_balance(self, user_id):
        self._ensure_account(user_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT wallet, bank FROM economia WHERE user_id = ?', (str(user_id),))
        resultado = cursor.fetchone()
        conn.close()
        return resultado if resultado else (0, 0)

    def _update_money(self, user_id, amount, local="wallet"):
        self._ensure_account(user_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = f'UPDATE economia SET {local} = {local} + ? WHERE user_id = ?'
        cursor.execute(query, (amount, str(user_id)))
        conn.commit()
        conn.close()

    # --- COMANDOS DE BANCO (DEPOSITAR / SACAR) ---

    @app_commands.command(name="depositar", description="Guarda dinheiro da carteira no banco (Seguro)")
    @app_commands.describe(valor="Quantidade para depositar ou 'tudo'")
    async def depositar(self, interaction: discord.Interaction, valor: str):
        wallet, bank = self._get_balance(interaction.user.id)
        
        # Lógica para aceitar "tudo" ou número
        if valor.lower() in ["tudo", "all", "todas"]:
            quantidade = wallet
        else:
            try:
                quantidade = int(valor)
            except ValueError:
                return await interaction.response.send_message("❌ Digite um número válido ou 'tudo'.", ephemeral=True)

        if quantidade <= 0:
            return await interaction.response.send_message("❌ O valor deve ser maior que zero.", ephemeral=True)

        if wallet < quantidade:
            return await interaction.response.send_message(f"❌ Você só tem **{wallet} CP** na carteira.", ephemeral=True)

        # Operação de Depósito
        self._update_money(interaction.user.id, -quantidade, "wallet")
        self._update_money(interaction.user.id, quantidade, "bank")

        embed = discord.Embed(
            description=f"🏦 **Depósito realizado!**\nVocê guardou **{quantidade} CP** no banco.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sacar", description="Retira dinheiro do banco para a carteira (Uso)")
    @app_commands.describe(valor="Quantidade para sacar ou 'tudo'")
    async def sacar(self, interaction: discord.Interaction, valor: str):
        wallet, bank = self._get_balance(interaction.user.id)

        if valor.lower() in ["tudo", "all", "todas"]:
            quantidade = bank
        else:
            try:
                quantidade = int(valor)
            except ValueError:
                return await interaction.response.send_message("❌ Digite um número válido ou 'tudo'.", ephemeral=True)

        if quantidade <= 0:
            return await interaction.response.send_message("❌ O valor deve ser maior que zero.", ephemeral=True)

        if bank < quantidade:
            return await interaction.response.send_message(f"❌ Você só tem **{bank} CP** no banco.", ephemeral=True)

        # Operação de Saque
        self._update_money(interaction.user.id, -quantidade, "bank")
        self._update_money(interaction.user.id, quantidade, "wallet")

        embed = discord.Embed(
            description=f"💸 **Saque realizado!**\nVocê retirou **{quantidade} CP** para a carteira.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    # --- OUTROS COMANDOS (SALDO / PAGAR) ---

    @app_commands.command(name="saldo", description="Verifique sua conta bancária e carteira")
    @app_commands.describe(usuario="Usuário para consultar (opcional)")
    async def saldo(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        wallet, bank = self._get_balance(target.id)
        total = wallet + bank

        embed = discord.Embed(title=f"💰 Finanças de {target.display_name}", color=discord.Color.gold())
        embed.add_field(name="💵 Carteira", value=f"{wallet} CP", inline=True)
        embed.add_field(name="🏦 Banco", value=f"{bank} CP", inline=True)
        embed.add_field(name="💎 Patrimônio Total", value=f"**{total} CP**", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pagar", description="Transfere dinheiro da sua carteira para outro usuário")
    async def pagar(self, interaction: discord.Interaction, usuario: discord.Member, valor: int):
        if valor <= 0:
            return await interaction.response.send_message("❌ O valor deve ser positivo.", ephemeral=True)
        
        if usuario.id == interaction.user.id:
            return await interaction.response.send_message("❌ Você não pode pagar a si mesmo.", ephemeral=True)

        pagador_wallet, _ = self._get_balance(interaction.user.id)

        if pagador_wallet < valor:
            return await interaction.response.send_message(f"❌ Saldo insuficiente na carteira (Tens: {pagador_wallet} CP).", ephemeral=True)

        self._update_money(interaction.user.id, -valor, "wallet")
        self._update_money(usuario.id, valor, "wallet")

        embed = discord.Embed(
            description=f"✅ **Pagamento Realizado!**\n\n{interaction.user.mention} pagou **{valor} CP** para {usuario.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # --- COMANDOS ADMIN ---

    @app_commands.command(name="eco_add", description="ADMIN: Adiciona dinheiro (Imprimir Dinheiro)")
    @app_commands.checks.has_permissions(administrator=True) 
    async def eco_add(self, interaction: discord.Interaction, usuario: discord.Member, valor: int, local: str = "wallet"):
        if local not in ["wallet", "bank"]:
            return await interaction.response.send_message("❌ Local inválido. Use 'wallet' ou 'bank'.", ephemeral=True)
        
        self._update_money(usuario.id, valor, local)
        await interaction.response.send_message(f"✅ Adicionado **{valor} CP** ao {local} de {usuario.mention}.", ephemeral=True)

    @app_commands.command(name="eco_remove", description="ADMIN: Remove dinheiro")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_remove(self, interaction: discord.Interaction, usuario: discord.Member, valor: int, local: str = "wallet"):
        if local not in ["wallet", "bank"]:
            return await interaction.response.send_message("❌ Local inválido. Use 'wallet' ou 'bank'.", ephemeral=True)
        
        self._update_money(usuario.id, -valor, local)
        await interaction.response.send_message(f"🔻 Removido **{valor} CP** do {local} de {usuario.mention}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyCore(bot))