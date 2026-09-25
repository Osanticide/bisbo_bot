import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta

class EconomyGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cindy_database.db"
        self._criar_tabelas_jogos()

        # --- VARIÁVEIS DA ROLETA (Estado na Memória) ---
        self.roulette_active = False
        self.roulette_bets = [] 
        self.ROULETTE_REDS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        self.ROULETTE_BLACKS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

    def _criar_tabelas_jogos(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela Jackpot
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jackpot (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                valor INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('INSERT OR IGNORE INTO jackpot (id, valor) VALUES (1, 0)')

        # Tabela Pools
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bet_pools (
                pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                criador_id TEXT,
                titulo TEXT,
                status TEXT DEFAULT 'ABERTO',
                opcoes TEXT
            )
        ''')

        # Tabela Pool Bets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pool_bets (
                pool_id INTEGER,
                user_id TEXT,
                opcao_escolhida TEXT,
                valor INTEGER
            )
        ''')

        # Tabela Limite de Jogadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_limits (
                user_id TEXT,
                game TEXT,
                count INTEGER DEFAULT 0,
                reset_time TEXT,
                PRIMARY KEY (user_id, game)
            )
        ''')

        conn.commit()
        conn.close()

    # --- MÉTODOS FINANCEIROS AUXILIARES ---

    def _get_saldo(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT wallet FROM economia WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def _transacao(self, user_id, valor):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE economia SET wallet = wallet + ? WHERE user_id = ?', (valor, str(user_id)))
        conn.commit()
        conn.close()

    def _atualizar_jackpot(self, valor):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE jackpot SET valor = valor + ? WHERE id = 1', (valor,))
        conn.commit()
        conn.close()

    # --- SISTEMA DE LIMITE ---

    def _verificar_limite(self, user_id, game, max_plays, period_hours=1):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT count, reset_time FROM game_limits WHERE user_id = ? AND game = ?', (str(user_id), game))
        result = cursor.fetchone()

        agora = datetime.now()

        if not result:
            reset_time = (agora + timedelta(hours=period_hours)).isoformat()
            cursor.execute('INSERT INTO game_limits VALUES (?, ?, 1, ?)', (str(user_id), game, reset_time))
            conn.commit()
            conn.close()
            return True, f"Jogada 1/{max_plays}"

        count, reset_str = result
        reset_time = datetime.fromisoformat(reset_str)

        if agora > reset_time:
            new_reset = (agora + timedelta(hours=period_hours)).isoformat()
            cursor.execute('UPDATE game_limits SET count = 1, reset_time = ? WHERE user_id = ? AND game = ?', 
                           (new_reset, str(user_id), game))
            conn.commit()
            conn.close()
            return True, f"Jogada 1/{max_plays}"

        if count >= max_plays:
            conn.close()
            restante = reset_time - agora
            minutos = int(restante.total_seconds() // 60)
            return False, f"Volte em {minutos} minutos."
        
        cursor.execute('UPDATE game_limits SET count = count + 1 WHERE user_id = ? AND game = ?', (str(user_id), game))
        conn.commit()
        conn.close()
        return True, f"Jogada {count + 1}/{max_plays}"

    # --- JOGOS DE CASSINO ---

    @app_commands.command(name="jackpot_check", description="Vê quanto está acumulado no prêmio máximo")
    async def jackpot_check(self, interaction: discord.Interaction):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM jackpot WHERE id = 1')
        valor = cursor.fetchone()[0]
        conn.close()
        
        embed = discord.Embed(title="🎰 JACKPOT GLOBAL", color=discord.Color.gold())
        embed.description = f"O prêmio acumulado está em:\n# 💰 {valor:,} CP".replace(",", ".")
        embed.set_footer(text="Jogue no cassino para fazer este valor subir!")
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Aposte no Cara ou Coroa (50% de chance)")
    @app_commands.choices(escolha=[
        app_commands.Choice(name="Cara (Heads)", value="cara"),
        app_commands.Choice(name="Coroa (Tails)", value="coroa")
    ])
    async def coinflip(self, interaction: discord.Interaction, escolha: app_commands.Choice[str], valor: int):
        user_id = interaction.user.id
        if valor <= 0: return await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
        saldo = self._get_saldo(user_id)
        if saldo < valor: return await interaction.response.send_message(f"❌ Saldo insuficiente.", ephemeral=True)

        resultado = random.choice(["cara", "coroa"])
        venceu = (escolha.value == resultado)

        if venceu:
            lucro = valor 
            self._transacao(user_id, lucro)
            embed = discord.Embed(title="🪙 Cara ou Coroa", color=discord.Color.green())
            embed.description = f"{interaction.user.mention} jogou a moeda e deu **{resultado.upper()}**!\n**GANHOU {valor} CP!**"
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
        else:
            self._transacao(user_id, -valor)
            taxa_jackpot = int(valor * 0.1)
            self._atualizar_jackpot(taxa_jackpot)
            embed = discord.Embed(title="🪙 Cara ou Coroa", color=discord.Color.red())
            embed.description = f"{interaction.user.mention} jogou a moeda e deu **{resultado.upper()}**!\nPerdeu **{valor} CP**."
            embed.set_footer(text=f"💸 {taxa_jackpot} CP foram para o Jackpot.")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Caça-Níqueis Hardcore: Risco Alto!")
    async def slots(self, interaction: discord.Interaction, valor: int):
        user_id = interaction.user.id
        
        if valor <= 0: return await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
        if self._get_saldo(user_id) < valor: return await interaction.response.send_message("❌ Saldo insuficiente.", ephemeral=True)

        # Limite de 10 Jogadas
        pode_jogar, msg_limite = self._verificar_limite(user_id, "slots", max_plays=10, period_hours=1)
        if not pode_jogar:
            return await interaction.response.send_message(f"⛔ **Limite Atingido!**\n{msg_limite}", ephemeral=True)

        # --- LÓGICA HARDCORE ---
        simbolos = (
            ["💎"] * 1 + ["7️⃣"] * 2 + ["🔔"] * 3 +
            ["🍒"] * 5 + ["🍇"] * 5 + ["🍋"] * 5 +
            ["💀"] * 10 + ["💩"] * 10
        )

        c1 = random.choice(simbolos)
        c2 = random.choice(simbolos)
        c3 = random.choice(simbolos)

        multiplicador = 0
        venceu = False
        msg_extra = ""

        # 1. Trincas (Jackpots)
        if c1 == c2 == c3:
            if c1 == "💎": multiplicador = 50 # SUPER JACKPOT
            elif c1 == "7️⃣": multiplicador = 20
            elif c1 == "🔔": multiplicador = 15
            elif c1 in ["🍒", "🍇", "🍋"]: multiplicador = 5
            elif c1 in ["💀", "💩"]: 
                multiplicador = 0 
                msg_extra = "💀 Trinca da Morte!"
            
            if multiplicador > 0: venceu = True

        # 2. Pares
        elif c1 == c2 or c2 == c3 or c1 == c3:
            if c1 == c2 or c1 == c3: par = c1
            else: par = c2
            
            if par == "💎": 
                multiplicador = 5
                venceu = True
            elif par == "7️⃣": 
                multiplicador = 3
                venceu = True
            elif par == "🔔":
                multiplicador = 2
                venceu = True
            else:
                multiplicador = 0
                venceu = False
                msg_extra = "Par fraco não paga nada!"

        # Transação e Visual
        if venceu:
            ganho = (valor * multiplicador) - valor 
            self._transacao(user_id, ganho)
            cor = discord.Color.green()
            texto_resultado = f"**WIN!** Multiplicador: **x{multiplicador}**\n{interaction.user.mention} ganhou **{valor * multiplicador} CP**!"
        else:
            self._transacao(user_id, -valor)
            taxa_jackpot = int(valor * 0.1)
            self._atualizar_jackpot(taxa_jackpot)
            cor = discord.Color.dark_red()
            
            complemento = f"\n*{msg_extra}*" if msg_extra else ""
            texto_resultado = f"{interaction.user.mention} perdeu **{valor} CP**.{complemento}"

        embed = discord.Embed(title="🎰 Casino Slots (Hard)", color=cor)
        embed.description = f"# ║ {c1} ║ {c2} ║ {c3} ║\n\n{texto_resultado}"
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"{msg_limite} | Taxa da Casa: 10%")
        
        await interaction.response.send_message(embed=embed)

    # --- AUTOCOMPLETE: POOL ID ---
    async def pool_id_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
        """Sugere Pools ABERTOS baseados no título ou ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT pool_id, titulo FROM bet_pools WHERE status = 'ABERTO' ORDER BY pool_id DESC LIMIT 25")
        pools = cursor.fetchall()
        conn.close()

        choices = []
        for pid, titulo in pools:
            display_name = f"#{pid} - {titulo}"
            if current.lower() in display_name.lower():
                choices.append(app_commands.Choice(name=display_name, value=pid))
        
        return choices[:25]

    # --- AUTOCOMPLETE: OPÇÕES ---
    async def pool_opcao_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Sugere as opções baseadas no Pool ID que o usuário JÁ selecionou"""
        
        pool_id = interaction.namespace.pool_id
        
        if not pool_id:
            return [app_commands.Choice(name="⚠️ Selecione o Pool ID primeiro!", value="erro")]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT opcoes FROM bet_pools WHERE pool_id = ?", (pool_id,))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            return []

        lista_opcoes = resultado[0].split(',')
        
        choices = []
        for opt in lista_opcoes:
            opt = opt.strip()
            if current.lower() in opt.lower():
                choices.append(app_commands.Choice(name=opt, value=opt))
        
        return choices[:25]

    # --- BET POOL ---

    @app_commands.command(name="pool_start", description="Inicia um Sorteio/Aposta. Preencha pelo menos as opções 1 e 2.")
    @app_commands.describe(
        titulo="O título ou pergunta da aposta",
        op1="Primeira opção (Obrigatória)",
        op2="Segunda opção (Obrigatória)",
        op3="Opção extra (Opcional)",
        op4="Opção extra (Opcional)",
        op5="Opção extra (Opcional)",
    )
    async def pool_start(self, interaction: discord.Interaction, 
                         titulo: str, 
                         op1: str, 
                         op2: str, 
                         op3: str = None, op4: str = None, op5: str = None, 
                         op6: str = None, op7: str = None, op8: str = None, 
                         op9: str = None, op10: str = None, op11: str = None, 
                         op12: str = None, op13: str = None, op14: str = None, 
                         op15: str = None, op16: str = None, op17: str = None, 
                         op18: str = None, op19: str = None, op20: str = None):
        
        # 1. Coleta e Limpeza
        entradas = [op1, op2, op3, op4, op5, op6, op7, op8, op9, op10, 
                    op11, op12, op13, op14, op15, op16, op17, op18, op19, op20]
        
        lista_opcoes = []
        for opt in entradas:
            if opt:
                texto_limpo = opt.strip().replace(",", "")
                if texto_limpo:
                    lista_opcoes.append(texto_limpo)

        # 2. Validação
        if len(lista_opcoes) < 2: 
            return await interaction.response.send_message("❌ É necessário fornecer no mínimo 2 opções válidas.", ephemeral=True)

        # 3. Salva no Banco
        opcoes_string = ",".join(lista_opcoes)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bet_pools (criador_id, titulo, opcoes, status) VALUES (?, ?, ?, ?)', 
                       (str(interaction.user.id), titulo, opcoes_string, 'ABERTO'))
        pool_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 4. Embed
        embed = discord.Embed(
            title=f"📊 Novo Sorteio/Aposta: #{pool_id}", 
            description=f"**{titulo}**\n\n" + "\n".join([f"🔹 `{opt}`" for opt in lista_opcoes]), 
            color=discord.Color.blurple()
        )
        embed.add_field(name="Como Participar", value=f"`/pool_bet {pool_id} [Opção] [Valor]`", inline=False)
        embed.set_footer(text="O resultado será SORTEADO aleatoriamente entre as opções.")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pool_bet", description="Aposta em um Pool")
    @app_commands.autocomplete(pool_id=pool_id_autocomplete, opcao=pool_opcao_autocomplete)
    async def pool_bet(self, interaction: discord.Interaction, pool_id: int, opcao: str, valor: int):
        
        if opcao == "erro":
            return await interaction.response.send_message("❌ Selecione o Pool ID primeiro!", ephemeral=True)

        if valor <= 0: return await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
        if self._get_saldo(interaction.user.id) < valor: return await interaction.response.send_message("❌ Sem saldo.", ephemeral=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT status, opcoes FROM bet_pools WHERE pool_id = ?', (pool_id,))
        pool = cursor.fetchone()
        
        if not pool or pool[0] != 'ABERTO': 
            conn.close()
            return await interaction.response.send_message("❌ Pool fechado ou inexistente.", ephemeral=True)
        
        opcoes_validas = [o.strip().lower() for o in pool[1].split(',')]
        if opcao.lower() not in opcoes_validas:
            conn.close()
            return await interaction.response.send_message(f"❌ Opção inválida! Escolha uma das sugestões.", ephemeral=True)
        
        self._transacao(interaction.user.id, -valor)
        cursor.execute('INSERT INTO pool_bets VALUES (?, ?, ?, ?)', (pool_id, str(interaction.user.id), opcao.lower(), valor))
        
        # Conta apostas para o Hype
        cursor.execute('SELECT COUNT(*) FROM pool_bets WHERE pool_id = ?', (pool_id,))
        total_apostas = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        # Resposta Pública com Hype
        await interaction.response.send_message(
            f"📢 **{interaction.user.display_name}** entrou na disputa!\n"
            f"💸 Valor: **{valor} CP** na opção `{opcao}`\n"
            f"🔥 Já são **{total_apostas}** participantes neste Pool!",
            ephemeral=False
        )
        
        # Reações
        mensagem = await interaction.original_response()
        try:
            await mensagem.add_reaction("👀")
            await mensagem.add_reaction("💸")
        except:
            pass

    @app_commands.command(name="pool_finish", description="Sorteia um vencedor aleatório e encerra o Pool (Criador)")
    @app_commands.autocomplete(pool_id=pool_id_autocomplete)
    async def pool_finish(self, interaction: discord.Interaction, pool_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT criador_id, status, opcoes FROM bet_pools WHERE pool_id = ?', (pool_id,))
        pool = cursor.fetchone()
        
        # Validações
        if not pool: return await interaction.response.send_message("❌ Pool não encontrado.", ephemeral=True)
        if str(interaction.user.id) != pool[0]: return await interaction.response.send_message("❌ Apenas o criador pode encerrar.", ephemeral=True)
        if pool[1] != 'ABERTO': return await interaction.response.send_message("❌ Este pool já foi encerrado.", ephemeral=True)
        
        # --- LÓGICA DE SORTEIO ALEATÓRIO ---
        opcoes_originais = [o.strip() for o in pool[2].split(',')] # Preserva maiúsculas para exibir
        vencedor_nome = random.choice(opcoes_originais) # Sorteia um
        venc_logica = vencedor_nome.lower() # Converte para buscar no banco

        cursor.execute('SELECT SUM(valor) FROM pool_bets WHERE pool_id = ?', (pool_id,))
        total_pote = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT user_id, valor FROM pool_bets WHERE pool_id = ? AND opcao_escolhida = ?', (pool_id, venc_logica))
        ganhadores = cursor.fetchall()
        
        total_apostado_vencedor = sum([g[1] for g in ganhadores])
        
        log = f"🎲 A roleta girou e parou em...\n# 🏆 **{vencedor_nome.upper()}**\n\n💰 Pote Total: **{total_pote} CP**\n\n"
        cor = discord.Color.gold()
        
        if total_apostado_vencedor == 0:
            self._atualizar_jackpot(total_pote)
            log += "💀 **Ninguém apostou nessa opção!** O pote foi para o Jackpot da casa."
            cor = discord.Color.red()
        else:
            for uid, val_apostado in ganhadores:
                # Divisão proporcional
                premio = int((val_apostado / total_apostado_vencedor) * total_pote)
                self._transacao(uid, premio)
                log += f"🎉 <@{uid}> ganhou **{premio} CP** (Apostou {val_apostado})\n"
        
        cursor.execute("UPDATE bet_pools SET status = 'FECHADO' WHERE pool_id = ?", (pool_id,))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(title=f"🏁 Resultado Pool #{pool_id}", description=log, color=cor)
        await interaction.response.send_message(embed=embed)

    # --- AUTOCOMPLETE DA ROLETA ---
    async def roulette_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Sugere números (0, 00, 1-36) e Cores"""
        opcoes = ["Vermelho", "Preto", "0", "00"] + [str(i) for i in range(1, 37)]
        
        choices = []
        for opt in opcoes:
            if current.lower() in opt.lower():
                choices.append(app_commands.Choice(name=opt, value=opt))
        
        return choices[:25] # Limite do Discord

    # --- COMANDOS DA ROLETA (Versão PvP: Pote Dividido) ---

    @app_commands.command(name="roulette_start", description="Abre a mesa de Roleta.")
    async def roulette_start(self, interaction: discord.Interaction):
        if self.roulette_active:
            return await interaction.response.send_message("❌ Já existe uma roleta girando! Espere acabar.", ephemeral=True)

        self.roulette_active = True
        self.roulette_bets = []

        embed = discord.Embed(title="🎰 Roleta da Cindy", color=discord.Color.dark_green())
        embed.description = (
            "Façam suas apostas!\n\n"
            "👤 **JOGANDO SOZINHO:**\n"
            "• Cor (2x) | Número (10x)\n\n"
            "👥 **EM GRUPO (PvP):**\n"
            "• O vencedor leva TODO o dinheiro da mesa!\n"
            "• Acertar número garante uma fatia maior do pote!\n\n"
            "⚠️ **REGRA DA CASA:** 0 ou 00 (Verde) = Cindy leva tudo!\n\n"
            "Use: `/roulette_bet [Aposta] [Valor]`"
        )
        embed.set_footer(text="A mesa será girada em breve...")
        
        try:
            arquivo = discord.File("images/roulette/table.png", filename="table.png")
            embed.set_image(url="attachment://table.png")
            await interaction.response.send_message(file=arquivo, embed=embed)
        except FileNotFoundError:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roulette_bet", description="Aposte na Roleta")
    @app_commands.autocomplete(escolha=roulette_autocomplete)
    async def roulette_bet(self, interaction: discord.Interaction, escolha: str, valor: int):
        if not self.roulette_active:
            return await interaction.response.send_message("❌ A roleta está fechada. Use /roulette_start primeiro.", ephemeral=True)
        
        if valor <= 0: return await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
        if self._get_saldo(interaction.user.id) < valor: return await interaction.response.send_message("❌ Saldo insuficiente.", ephemeral=True)

        # Validação da Escolha
        escolha_limpa = escolha.strip().title() # "vermelho " -> "Vermelho"
        validos = ["Vermelho", "Preto", "0", "00"] + [str(i) for i in range(1, 37)]
        
        if escolha_limpa not in validos:
            return await interaction.response.send_message("❌ Aposta inválida! Escolha Vermelho, Preto ou um número.", ephemeral=True)

        # Cobra o valor e registra a aposta
        self._transacao(interaction.user.id, -valor)
        
        self.roulette_bets.append({
            'user_id': interaction.user.id,
            'name': interaction.user.display_name,
            'choice': escolha_limpa,
            'amount': valor
        })

        # Hype público
        await interaction.response.send_message(
            f"🎲 **{interaction.user.display_name}** colocou **{valor} CP** no **{escolha_limpa}**!",
            ephemeral=False
        )

    @app_commands.command(name="roulette_finish", description="Gira a roleta e distribui o prêmio!")
    async def roulette_finish(self, interaction: discord.Interaction):
        if not self.roulette_active:
            return await interaction.response.send_message("❌ Não há roleta aberta para girar.", ephemeral=True)

        self.roulette_active = False 
        
        # 1. Animação
        embed_spin = discord.Embed(title="🎡 A Roleta está girando...", color=discord.Color.gold())
        try:
            arquivo_gif = discord.File("images/roulette/spin.gif", filename="spin.gif")
            embed_spin.set_image(url="attachment://spin.gif")
            await interaction.response.send_message(file=arquivo_gif, embed=embed_spin)
        except FileNotFoundError:
            await interaction.response.send_message("🎡 **Girando...** (GIF não encontrado)")

        await asyncio.sleep(4)

        # 2. Sorteio
        casas_possiveis = ["0", "00"] + [str(i) for i in range(1, 37)]
        resultado_str = random.choice(casas_possiveis)
        
        cor_resultado = "Verde" 
        if resultado_str not in ["0", "00"]:
            num = int(resultado_str)
            if num in self.ROULETTE_REDS: cor_resultado = "Vermelho"
            elif num in self.ROULETTE_BLACKS: cor_resultado = "Preto"

        emoji_cor = "🟢"
        cor_embed = discord.Color.green()
        if cor_resultado == "Vermelho": 
            emoji_cor = "🔴"
            cor_embed = discord.Color.red()
        elif cor_resultado == "Preto": 
            emoji_cor = "⚫"
            cor_embed = discord.Color.default()

        # 3. Lógica de Pagamento
        log_vencedores = ""
        total_bets = sum(b['amount'] for b in self.roulette_bets)
        
        # --- CENÁRIO 1: CINDY LEVA TUDO (0 ou 00) ---
        if resultado_str in ["0", "00"]:
            self._atualizar_jackpot(int(total_bets * 0.5))
            log_vencedores = f"💀 **CASA DA CINDY!** Deu {resultado_str}.\n💸 A banca recolheu todas as apostas ({total_bets} CP)."

        # --- CENÁRIO 2: MODO SOLO (1 Jogador apenas) ---
        elif len(self.roulette_bets) == 1:
            bet = self.roulette_bets[0]
            uid = bet['user_id']
            escolha = bet['choice']
            valor = bet['amount']
            
            ganhou = False
            multiplicador = 0

            if escolha == resultado_str: # Acertou Número
                multiplicador = 10
                ganhou = True
            elif escolha == cor_resultado: # Acertou Cor
                multiplicador = 2
                ganhou = True
            
            if ganhou:
                premio = valor * multiplicador
                self._transacao(uid, premio)
                log_vencedores = f"🎉 <@{uid}> jogou sozinho e ganhou **{premio} CP** (x{multiplicador})!"
            else:
                log_vencedores = "💀 Você perdeu para a banca."
                self._atualizar_jackpot(int(valor * 0.2))

        # --- CENÁRIO 3: MULTIPLAYER (Divisão do Pote) ---
        else:
            vencedores = []
            peso_total_vencedores = 0
            
            for bet in self.roulette_bets:
                acertou_numero = (bet['choice'] == resultado_str)
                acertou_cor = (bet['choice'] == cor_resultado)
                
                if acertou_numero or acertou_cor:
                    # Sistema de Peso: Número vale 35x mais "ações" do pote que a Cor
                    peso = bet['amount']
                    if acertou_numero:
                        peso = peso * 15 # Bônus por dificuldade
                    
                    vencedores.append({'uid': bet['user_id'], 'peso': peso})
                    peso_total_vencedores += peso
            
            if not vencedores:
                log_vencedores = f"💀 A casa venceu. Ninguém acertou o {resultado_str} ({cor_resultado})."
                self._atualizar_jackpot(int(total_bets * 0.2))
            else:
                log_vencedores += f"💰 **POTE TOTAL: {total_bets} CP**\n\n"
                for v in vencedores:
                    # Divisão proporcional ao peso (Quem apostou número leva muito mais)
                    share = v['peso'] / peso_total_vencedores
                    premio = int(total_bets * share)
                    self._transacao(v['uid'], premio)
                    log_vencedores += f"🎉 <@{v['uid']}> levou **{premio} CP**\n"

        # 4. Resultado Final
        embed_final = discord.Embed(
            title=f"🎰 Resultado: {emoji_cor} {resultado_str} ({cor_resultado})",
            description=f"**Resumo da Rodada:**\n{log_vencedores}",
            color=cor_embed
        )
        embed_final.set_footer(text="Use /roulette_start para tentar recuperar o prejuízo.")
        
        await interaction.followup.send(embed=embed_final)
    
async def setup(bot):
    await bot.add_cog(EconomyGames(bot))