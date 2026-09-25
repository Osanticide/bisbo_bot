import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
from datetime import datetime, timedelta
from utils.interface import Paginator 

class EconomyJobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self._criar_tabelas_jobs()
        self.jobs_config = self._definir_empregos()

    def _criar_tabelas_jobs(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # MUDANÇA: Tabela renomeada para 'jobs' e coluna para 'job_name' para compatibilidade com /perfil
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                user_id TEXT PRIMARY KEY,
                job_name TEXT, 
                hire_date TEXT,
                licenses TEXT DEFAULT ''
            )
        ''')
        # Garante a tabela de cooldowns
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

    def _definir_empregos(self):
        """
        Configuração completa dos empregos.
        Tier 4 = Ilegal.
        """
        return {
            # --- TIER 1: INICIANTE (Grátis / CD: 1h) ---
            'lixeiro': {'nome': 'Lixeiro', 'tier': 1, 'custo': 0, 'min': 30, 'max': 50, 'cd': 1, 'emoji': '🗑️', 'desc': 'O trabalho honesto que ninguém quer fazer.'},
            'entregador': {'nome': 'Entregador', 'tier': 1, 'custo': 0, 'min': 35, 'max': 55, 'cd': 1, 'emoji': '🛵', 'desc': 'Correndo risco de vida pra entregar lanche frio.'},
            'flanelinha': {'nome': 'Flanelinha', 'tier': 1, 'custo': 0, 'min': 25, 'max': 45, 'cd': 1, 'emoji': '🧢', 'desc': 'Vigia seu carro, chefe?'},
            'discordmod': {'nome': 'Discord Mod', 'tier': 1, 'custo': 0, 'min': 40, 'max': 60, 'cd': 1, 'emoji': '🛡️', 'desc': 'Trabalha de graça limpando chat e bane por poder.'},
            'cobaia': {'nome': 'Cobaia Humana', 'tier': 1, 'custo': 0, 'min': 50, 'max': 80, 'cd': 1, 'emoji': '🧪', 'desc': 'Vende o corpo para testar remédios duvidosos.'},
            'pack': {'nome': 'Vendedor de Pack', 'tier': 1, 'custo': 0, 'min': 45, 'max': 75, 'cd': 1, 'emoji': '📸', 'desc': 'Vende fotos do pé. É dinheiro fácil, mas a dignidade vai embora.'},

            # --- TIER 2: INTERMEDIÁRIO (Custo: Médio / CD: 3-4h) ---
            'pescador': {'nome': 'Pescador', 'tier': 2, 'custo': 1500, 'min': 150, 'max': 220, 'cd': 3, 'emoji': '🎣', 'desc': 'O clássico relaxante. Pega peixe e bota velha.'},
            'fofoqueiro': {'nome': 'Fofoqueiro', 'tier': 2, 'custo': 1500, 'min': 140, 'max': 210, 'cd': 3, 'emoji': '👀', 'desc': 'Ganha dinheiro vendendo segredos dos outros.'},
            'youtuber': {'nome': 'Youtuber Falido', 'tier': 2, 'custo': 1800, 'min': 100, 'max': 300, 'cd': 3, 'emoji': '📹', 'desc': 'Faz vídeo de React e implora por like.'},
            'uber': {'nome': 'Motorista de App', 'tier': 2, 'custo': 2000, 'min': 160, 'max': 240, 'cd': 3, 'emoji': '🚗', 'desc': 'Ouve desabafo de passageiro e ganha bala.'},
            'coach': {'nome': 'Coach Quântico', 'tier': 2, 'custo': 2500, 'min': 200, 'max': 350, 'cd': 4, 'emoji': '🧠', 'desc': 'Ensina a reprogramar o DNA para ficar rico.'},
            'golpista': {'nome': 'Golpista do Tinder', 'tier': 2, 'custo': 2200, 'min': 180, 'max': 320, 'cd': 4, 'emoji': '💔', 'desc': 'Jantares caros pagos por iludidos.'},

            # --- TIER 3: ELITE (Custo: Alto / CD: 12-24h) ---
            'medico': {'nome': 'Médico', 'tier': 3, 'custo': 10000, 'min': 900, 'max': 1200, 'cd': 12, 'emoji': '🩺', 'desc': 'Plantões intermináveis, mas o CRM canta alto.'},
            'pastor': {'nome': 'Pastor de TV', 'tier': 3, 'custo': 15000, 'min': 1200, 'max': 1800, 'cd': 12, 'emoji': '🙏', 'desc': 'Pede o dízimo via Pix na televisão.'},
            'agiota': {'nome': 'Agiota', 'tier': 3, 'custo': 20000, 'min': 1800, 'max': 2800, 'cd': 18, 'emoji': '💼', 'desc': 'Empresta dinheiro a juros... a cobrança é física.'},
            'banqueiro': {'nome': 'Banqueiro', 'tier': 3, 'custo': 25000, 'min': 2500, 'max': 3500, 'cd': 24, 'emoji': '🏦', 'desc': 'O dono do sistema. Lucra enquanto dorme.'},
            'donobet': {'nome': 'Dono de Bet', 'tier': 3, 'custo': 30000, 'min': 3000, 'max': 4500, 'cd': 24, 'emoji': '🐯', 'desc': 'Criador do Jogo do Tigrinho. A casa sempre vence.'},

            # --- TIER 4: ILEGAL (Alto Risco / Falha 55%) ---
            'ladrao': {'nome': 'Ladrão', 'tier': 4, 'custo': 5000, 'min': 500, 'max': 900, 'cd': 2, 'emoji': '🥷', 'desc': 'Rouba carteiras no centro.'},
            'hacker': {'nome': 'Hacker', 'tier': 4, 'custo': 15000, 'min': 800, 'max': 1500, 'cd': 4, 'emoji': '💻', 'desc': 'Invade contas bancárias.'},
            'traficante': {'nome': 'Traficante de Arte', 'tier': 4, 'custo': 30000, 'min': 1000, 'max': 2500, 'cd': 6, 'emoji': '🖼️', 'desc': 'Vende quadros roubados no mercado negro.'},
        }

    # --- DATABASES HELPERS ---

    def _get_user_job(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # MUDANÇA: Consulta na tabela 'jobs' e coluna 'job_name'
        cursor.execute('SELECT job_name, hire_date, licenses FROM jobs WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        conn.close()
        if not result:
            return None, None, []
        
        job_id = result[0]
        hire_date = result[1]
        licenses = result[2].split(',') if result[2] else []
        return job_id, hire_date, licenses

    def _update_job(self, user_id, job_id, licenses_list):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        licenses_str = ",".join(licenses_list)
        now = datetime.now().isoformat()
        
        # MUDANÇA: Update na tabela 'jobs'
        cursor.execute('''
            INSERT INTO jobs (user_id, job_name, hire_date, licenses)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            job_name = excluded.job_name,
            hire_date = excluded.hire_date,
            licenses = excluded.licenses
        ''', (str(user_id), job_id, now, licenses_str))
        conn.commit()
        conn.close()

    def _update_wallet(self, user_id, amount):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Garante que o usuario exista na economia antes de atualizar
        cursor.execute('INSERT OR IGNORE INTO economia (user_id, wallet, banco) VALUES (?, 0, 0)', (str(user_id),))
        cursor.execute('UPDATE economia SET wallet = wallet + ? WHERE user_id = ?', (amount, str(user_id)))
        conn.commit()
        conn.close()

    def _check_wallet(self, user_id, amount):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT wallet FROM economia WHERE user_id = ?', (str(user_id),))
        res = cursor.fetchone()
        conn.close()
        if res and res[0] >= amount: return True
        return False

    def _check_cooldown(self, user_id, command_key, hours):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ultimo_uso FROM cooldowns WHERE user_id = ? AND comando = ?', (str(user_id), command_key))
        res = cursor.fetchone()
        conn.close()
        if not res: return True, None
        
        last_use = datetime.fromisoformat(res[0])
        now = datetime.now()
        diff = now - last_use
        if diff < timedelta(hours=hours):
            remaining = timedelta(hours=hours) - diff
            h, rem = divmod(remaining.seconds, 3600)
            m, _ = divmod(rem, 60)
            return False, f"{h}h {m}m"
        return True, None

    def _set_cooldown(self, user_id, command_key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, comando, ultimo_uso) VALUES (?, ?, ?)', 
                       (str(user_id), command_key, now))
        conn.commit()
        conn.close()

    # --- FACTORY PARA O PAGINATOR (A Loja por Tiers) ---
    async def _shop_embed_factory(self, tier, current_page, total_pages):
        """
        Recebe o número do Tier (1, 2, 3 ou 4) e monta a página da loja.
        """
        titulos = {
            1: "🟢 TIER 1: Início de Carreira (Grátis)",
            2: "🔵 TIER 2: Classe Trabalhadora",
            3: "🟣 TIER 3: A Elite",
            4: "🔴 SUBMUNDO: Alto Risco (Ilegal)"
        }
        cores = {
            1: discord.Color.green(),
            2: discord.Color.blue(),
            3: discord.Color.purple(),
            4: discord.Color.dark_red()
        }
        
        # Correção visual: light_grey em vez de gray
        embed = discord.Embed(title=titulos.get(tier, "Loja de Jobs"), color=cores.get(tier, discord.Color.light_grey()))
        
        if tier == 4:
            embed.description = "⚠️ **Zona de Perigo:** Estes trabalhos têm **55% de chance de FALHA**.\nSe falhar, você perde dinheiro (multa)."
        else:
            embed.description = "Use `/jobs_join id:[nome]` para comprar a licença e começar."

        # Filtra os jobs do tier atual
        jobs_do_tier = {k: v for k, v in self.jobs_config.items() if v['tier'] == tier}

        for job_id, data in jobs_do_tier.items():
            custo = "Grátis" if data['custo'] == 0 else f"{data['custo']} CP"
            
            # Formatação especial para ilegal
            if tier == 4:
                stats = f"💰 **Sucesso:** {data['min']} - {data['max']} CP\n💸 **Custo Licença:** {custo}\n⏱️ **CD:** {data['cd']}h"
            else:
                stats = f"💰 **Salário:** {data['min']} - {data['max']} CP\n🏷️ **Licença:** {custo}\n⏱️ **CD:** {data['cd']}h"

            embed.add_field(
                name=f"{data['emoji']} {data['nome']} (`{job_id}`)",
                value=f"{stats}\n*{data['desc']}*",
                inline=False
            )
        
        embed.set_footer(text=f"Página {current_page + 1} de {total_pages} (Navegue pelos Tiers)")
        # Retorna tupla (embed, file) -> file é None aqui
        return embed, None

    # --- COMANDOS ---

    @app_commands.command(name="loja_jobs", description="Abre a loja de licenças e profissões (Navegue por Tiers)")
    async def loja_jobs(self, interaction: discord.Interaction):
        # A lista de itens para o paginador são os números dos Tiers
        tiers = [1, 2, 3, 4]
        
        view = Paginator(interaction, tiers, self._shop_embed_factory)
        # O Paginator do utils.interface já lida com tuple no retorno
        embed, _ = await self._shop_embed_factory(tiers[0], 0, len(tiers))
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="carteira_trabalho", description="Vê seus empregos, licenças e tempo de contrato")
    async def carteira_trabalho(self, interaction: discord.Interaction):
        job_id, hire_date_str, licenses = self._get_user_job(interaction.user.id)
        
        embed = discord.Embed(title=f"🪪 Carteira de Trabalho de {interaction.user.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # 1. Situação Atual
        if job_id:
            job_data = self.jobs_config.get(job_id, {})
            nome_job = job_data.get('nome', 'Desconhecido')
            emoji = job_data.get('emoji', '❓')
            
            # Cálculo de Tempo Restante do Contrato
            hire_date = datetime.fromisoformat(hire_date_str)
            agora = datetime.now()
            tempo_casa = agora - hire_date
            
            if tempo_casa < timedelta(hours=48):
                restante = timedelta(hours=48) - tempo_casa
                h, _ = divmod(restante.seconds, 3600)
                status_contrato = f"🔒 **Bloqueado** (Restam {restante.days}d {h}h)"
            else:
                status_contrato = "🔓 **Livre** (Pode sair/trocar)"
            
            embed.add_field(name="💼 Emprego Atual", value=f"**{emoji} {nome_job}**", inline=False)
            embed.add_field(name="📅 Contrato (48h)", value=status_contrato, inline=False)
        else:
            embed.add_field(name="💼 Emprego Atual", value="*Desempregado*", inline=False)

        # 2. Lista de Licenças
        if licenses:
            # Agrupar licenças por nome bonito
            lista_formatada = []
            for lic in licenses:
                if lic in self.jobs_config:
                    d = self.jobs_config[lic]
                    lista_formatada.append(f"{d['emoji']} {d['nome']}")
            
            texto_licencas = "\n".join(lista_formatada)
            embed.add_field(name="📜 Licenças Adquiridas", value=texto_licencas, inline=False)
        else:
            embed.add_field(name="📜 Licenças Adquiridas", value="Nenhuma.", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="jobs_join", description="Entra em um emprego (Contrato de 48h!)")
    @app_commands.describe(job_id="O ID do emprego (ex: lixeiro, medico, ladrao)")
    async def jobs_join(self, interaction: discord.Interaction, job_id: str):
        job_id = job_id.lower()
        if job_id not in self.jobs_config:
            return await interaction.response.send_message("❌ Profissão não encontrada. Use `/loja_jobs`.", ephemeral=True)

        user_job, hire_date_str, licenses = self._get_user_job(interaction.user.id)
        job_data = self.jobs_config[job_id]

        # VERIFICA CONTRATO ATUAL
        if user_job:
            if user_job == job_id: return await interaction.response.send_message("❌ Você já trabalha nisso!", ephemeral=True)
            
            hire_date = datetime.fromisoformat(hire_date_str)
            agora = datetime.now()
            tempo_casa = agora - hire_date
            
            if tempo_casa < timedelta(hours=48):
                restante = timedelta(hours=48) - tempo_casa
                h, _ = divmod(restante.seconds, 3600)
                return await interaction.response.send_message(f"🚫 **Contrato Vigente!**\nVocê só pode trocar de emprego após 48h.\nRestam: **{restante.days}d {h}h**.", ephemeral=True)

        # VERIFICA / COMPRA LICENÇA
        if job_id not in licenses:
            custo = job_data['custo']
            if custo > 0:
                if not self._check_wallet(interaction.user.id, custo):
                    return await interaction.response.send_message(f"💸 Você precisa de **{custo} CP** para esta licença.", ephemeral=True)
                
                self._update_wallet(interaction.user.id, -custo)
                msg_licenca = f"✅ Licença comprada por **{custo} CP**."
            else:
                msg_licenca = "✅ Licença gratuita emitida."
            
            licenses.append(job_id)
        else:
            msg_licenca = "✅ Licença já possuída. Recontratação!"

        self._update_job(interaction.user.id, job_id, licenses)
        
        embed = discord.Embed(title=f"🤝 Contratado: {job_data['nome']}", color=discord.Color.green())
        embed.description = f"{msg_licenca}\nBem-vindo ao cargo de **{job_data['nome']}** {job_data['emoji']}!\n\n⚠️ **Atenção:** Contrato de 48h assinado.\nUse `/work` para trabalhar."
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Trabalha para ganhar dinheiro (ou perder, se for ilegal)")
    async def work(self, interaction: discord.Interaction):
        job_id, _, _ = self._get_user_job(interaction.user.id)
        
        if not job_id:
            return await interaction.response.send_message("❌ Você é desempregado! Use `/loja_jobs`.", ephemeral=True)

        job_data = self.jobs_config.get(job_id)
        if not job_data:
            return await interaction.response.send_message("❌ Emprego inválido.", ephemeral=True)

        # VERIFICA COOLDOWN
        pode_trabalhar, tempo_restante = self._check_cooldown(interaction.user.id, "work", job_data['cd'])
        if not pode_trabalhar:
             return await interaction.response.send_message(f"⏳ Você está descansando!\nVolte em **{tempo_restante}**.", ephemeral=True)

        # --- LÓGICA DE PAGAMENTO ---
        
        # Se for ILEGAL (Tier 4)
        if job_data['tier'] == 4:
            chance = random.randint(1, 100)
            
            # 45% de Sucesso (1 a 45)
            if chance <= 45:
                # SUCESSO
                salario = random.randint(job_data['min'], job_data['max'])
                self._update_wallet(interaction.user.id, salario)
                cor = discord.Color.green()
                texto = f"🥷 **Sucesso no crime!**\nVocê agiu como **{job_data['nome']}** e faturou **{salario} CP**!"
            else:
                # FALHA (55% de chance)
                perda = random.randint(200, 600) # Multa aleatória
                # Verifica se tem dinheiro pra pagar a multa, senão zera
                if not self._check_wallet(interaction.user.id, perda):
                    self._update_wallet(interaction.user.id, -999999) # Zera se não tiver
                
                self._update_wallet(interaction.user.id, -perda)
                cor = discord.Color.red()
                texto = f"🚓 **A polícia te pegou!**\nSua operação como **{job_data['nome']}** falhou.\nVocê pagou **{perda} CP** de suborno para sair livre."

        # Se for LEGAL (Tier 1, 2, 3)
        else:
            salario = random.randint(job_data['min'], job_data['max'])
            self._update_wallet(interaction.user.id, salario)
            cor = discord.Color.green()
            frases = ["trabalhou duro e recebeu", "cumpriu o expediente e ganhou", "fez o corre e levou"]
            texto = f"🔨 {interaction.user.mention} {random.choice(frases)} **{salario} CP** como **{job_data['nome']}**!"

        self._set_cooldown(interaction.user.id, "work")
        
        embed = discord.Embed(description=texto, color=cor)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resign", description="Pede demissão (Requer fim do contrato de 48h)")
    async def resign(self, interaction: discord.Interaction):
        job_id, hire_date_str, _ = self._get_user_job(interaction.user.id)
        
        if not job_id: return await interaction.response.send_message("❌ Você já não tem emprego.", ephemeral=True)

        hire_date = datetime.fromisoformat(hire_date_str)
        agora = datetime.now()
        tempo_casa = agora - hire_date
        
        if tempo_casa < timedelta(hours=48):
             restante = timedelta(hours=48) - tempo_casa
             h, _ = divmod(restante.seconds, 3600)
             return await interaction.response.send_message(f"🚫 **Contrato vigente!**\nMulta contratual ativa.\nEspere: **{restante.days}d {h}h**.", ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # MUDANÇA: Update na tabela 'jobs' e coluna 'job_name'
        cursor.execute('UPDATE jobs SET job_name = NULL WHERE user_id = ?', (str(interaction.user.id),))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"📄 {interaction.user.mention} pediu as contas e agora é **Desempregado**.")

async def setup(bot):
    await bot.add_cog(EconomyJobs(bot))