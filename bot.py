import discord
import random
import aiosqlite
from discord import app_commands
from datetime import datetime, timedelta
from discord.ui import Button, View

SEU_ID = 0  # Substitua pelo seu ID real

class ErosBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Cria ou atualiza as tabelas no banco de dados."""
        async with aiosqlite.connect("eros.db") as db:
            # Cria a tabela de personagens, se não existir
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personagens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    imagem TEXT NOT NULL,
                    conquistado INTEGER DEFAULT 0
                )
            """)
            # Cria a tabela de amores, se não existir
            await db.execute("""
                CREATE TABLE IF NOT EXISTS amores (
                    usuario_id INTEGER NOT NULL,
                    personagem TEXT NOT NULL COLLATE NOCASE UNIQUE
                )
            """)
            # Cria a tabela de cooldowns, se não existir
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cooldowns (
                    usuario_id INTEGER PRIMARY KEY,
                    tentativas INTEGER DEFAULT 0,
                    tempo TEXT,
                    ultimo_casamento TEXT,
                    ultimo_coletar TEXT  -- Nova coluna para armazenar o último uso do comando /coletar
                )
            """)
            # Adiciona a coluna `ultimo_coletar` se ela não existir
            try:
                await db.execute("ALTER TABLE cooldowns ADD COLUMN ultimo_coletar TEXT")
            except aiosqlite.OperationalError:
                pass  # A coluna já existe, não faz nada
            # Cria a tabela de moedas, se não existir
            await db.execute("""
                CREATE TABLE IF NOT EXISTS moedas (
                    usuario_id INTEGER PRIMARY KEY,
                    eritos INTEGER DEFAULT 0
                )
            """)
            # Cria a tabela de trocas, se não existir
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trocas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ofertante_id INTEGER NOT NULL,
                    personagem TEXT NOT NULL,
                    destinatario_id INTEGER NOT NULL,
                    quantidade_eritos INTEGER NOT NULL
                )
            """)
            await db.commit()
        await self.tree.sync()

    async def adicionar_personagem(self, nome, imagem):
        """Adiciona um personagem, garantindo que não haja repetição de nomes (ignorando maiúsculas/minúsculas)."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT 1 FROM personagens WHERE LOWER(nome) = LOWER(?)", (nome,))
            if await cursor.fetchone():
                return False  # Nome já existe
            await db.execute("INSERT INTO personagens (nome, imagem) VALUES (?, ?)", (nome, imagem))
            await db.commit()
            return True

    async def excluir_personagem(self, nome):
        """Exclui um personagem do banco de dados."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("DELETE FROM personagens WHERE nome = ?", (nome,))
            await db.execute("DELETE FROM amores WHERE personagem = ?", (nome,))
            await db.commit()

    async def listar_amores(self, usuario_id):
        """Lista os personagens conquistados por um usuário."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT personagem FROM amores WHERE usuario_id = ?", (usuario_id,))
            return [row[0] for row in await cursor.fetchall()]

    async def adicionar_amor(self, usuario_id, personagem):
        """Adiciona um personagem à lista de amores de um usuário e o marca como conquistado."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("INSERT INTO amores (usuario_id, personagem) VALUES (?, ?)", (usuario_id, personagem))
            await db.execute("UPDATE personagens SET conquistado = 1 WHERE nome = ?", (personagem,))
            await db.commit()

    async def obter_dono_personagem(self, nome):
        """Obtém o ID do usuário que conquistou determinado personagem."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT usuario_id FROM amores WHERE LOWER(personagem) = LOWER(?)", (nome,))
            dono = await cursor.fetchone()
            return dono[0] if dono else None

    async def liberar_personagem(self, usuario_id, personagem):
        """Remove o personagem da lista de amores do usuário e o torna disponível novamente."""
        async with aiosqlite.connect("eros.db") as db:
            dono = await self.obter_dono_personagem(personagem)
            if dono == usuario_id:
                await db.execute("DELETE FROM amores WHERE personagem = ?", (personagem,))
                await db.execute("UPDATE personagens SET conquistado = 0 WHERE nome = ?", (personagem,))
                await db.commit()
                return True
            return False

    async def limpar_todos_amores(self):
        """Remove todos os relacionamentos e marca todos os personagens como disponíveis."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("DELETE FROM amores")
            await db.execute("UPDATE personagens SET conquistado = 0")
            await db.commit()

    async def can_paquerar(self, usuario_id):
        """Verifica se o usuário pode usar o comando /paquerar."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT tentativas, tempo, ultimo_casamento FROM cooldowns WHERE usuario_id = ?", (usuario_id,))
            cooldown_info = await cursor.fetchone()

        if not cooldown_info:
            return True, None, None  # Nunca usou o comando antes

        tentativas, tempo_str, ultimo_casamento_str = cooldown_info
        tempo = datetime.fromisoformat(tempo_str) if tempo_str else None
        ultimo_casamento = datetime.fromisoformat(ultimo_casamento_str) if ultimo_casamento_str else None

        # Verifica se o cooldown de casamento já expirou
        if ultimo_casamento:
            tempo_restante_casamento = (ultimo_casamento + timedelta(hours=18)) - datetime.now()
            if tempo_restante_casamento > timedelta(0):
                return False, None, tempo_restante_casamento  # Ainda em cooldown de casamento

        # Verifica o cooldown de tentativas
        if tempo and datetime.now() > tempo:
            # Reinicia a contagem de tentativas
            await self.resetar_tentativas(usuario_id)
            return True, None, None

        if tentativas >= 5:  # Limite de tentativas aumentado para 5
            tempo_restante = tempo - datetime.now()
            if tempo_restante > timedelta(0):
                return False, tempo_restante, None  # Ainda em cooldown de tentativas

        return True, None, None

    async def resetar_tentativas(self, usuario_id):
        """Reinicia a contagem de tentativas e o tempo de cooldown."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("UPDATE cooldowns SET tentativas = 0, tempo = NULL WHERE usuario_id = ?", (usuario_id,))
            await db.commit()

    async def update_cooldown(self, usuario_id, casou=False):
        """Atualiza o cooldown do usuário após usar o comando /paquerar."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT tentativas FROM cooldowns WHERE usuario_id = ?", (usuario_id,))
            cooldown_info = await cursor.fetchone()

            if not cooldown_info:
                # Primeira tentativa
                await db.execute("INSERT INTO cooldowns (usuario_id, tentativas, tempo) VALUES (?, 1, ?)",
                                (usuario_id, (datetime.now() + timedelta(hours=18)).isoformat()))
            else:
                tentativas = cooldown_info[0] + 1
                if tentativas >= 5:  # Limite de tentativas aumentado para 5
                    await db.execute("UPDATE cooldowns SET tentativas = ?, tempo = ? WHERE usuario_id = ?",
                                    (tentativas, (datetime.now() + timedelta(hours=18)).isoformat(), usuario_id))
                else:
                    await db.execute("UPDATE cooldowns SET tentativas = ? WHERE usuario_id = ?",
                                    (tentativas, usuario_id))

            if casou:
                await db.execute("UPDATE cooldowns SET ultimo_casamento = ? WHERE usuario_id = ?",
                                (datetime.now().isoformat(), usuario_id))

            await db.commit()

    async def obter_eritos(self, usuario_id):
        """Obtém a quantidade de Eritos de um usuário."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT eritos FROM moedas WHERE usuario_id = ?", (usuario_id,))
            resultado = await cursor.fetchone()
            return resultado[0] if resultado else 0

    async def adicionar_eritos(self, usuario_id, quantidade):
        """Adiciona Eritos a um usuário."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("INSERT OR IGNORE INTO moedas (usuario_id, eritos) VALUES (?, 0)", (usuario_id,))
            await db.execute("UPDATE moedas SET eritos = eritos + ? WHERE usuario_id = ?", (quantidade, usuario_id))
            await db.commit()

    async def remover_eritos(self, usuario_id, quantidade):
        """Remove Eritos de um usuário."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("UPDATE moedas SET eritos = eritos - ? WHERE usuario_id = ?", (quantidade, usuario_id))
            await db.commit()

    async def criar_troca(self, ofertante_id, personagem, destinatario_id, quantidade_eritos):
        """Cria uma proposta de troca e retorna o ID da troca."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute(
                "INSERT INTO trocas (ofertante_id, personagem, destinatario_id, quantidade_eritos) VALUES (?, ?, ?, ?)",
                (ofertante_id, personagem, destinatario_id, quantidade_eritos)
            )
            await db.commit()
            return cursor.lastrowid  # Retorna o ID da troca

    async def confirmar_troca(self, troca_id):
        """Confirma uma troca e transfere o personagem e os Eritos."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT ofertante_id, personagem, destinatario_id, quantidade_eritos FROM trocas WHERE id = ?", (troca_id,))
            troca = await cursor.fetchone()

            if not troca:
                return False

            ofertante_id, personagem, destinatario_id, quantidade_eritos = troca

            # Verifica se o ofertante ainda possui o personagem
            dono = await self.obter_dono_personagem(personagem)
            if dono != ofertante_id:
                return False

            # Verifica se o destinatário tem Eritos suficientes
            eritos_destinatario = await self.obter_eritos(destinatario_id)
            if eritos_destinatario < quantidade_eritos:
                return False

            # Transfere o personagem
            await self.liberar_personagem(ofertante_id, personagem)
            await self.adicionar_amor(destinatario_id, personagem)

            # Transfere os Eritos
            await self.adicionar_eritos(ofertante_id, quantidade_eritos)
            await self.remover_eritos(destinatario_id, quantidade_eritos)

            # Remove a troca
            await db.execute("DELETE FROM trocas WHERE id = ?", (troca_id,))
            await db.commit()

            return True

    async def recusar_troca(self, troca_id):
        """Recusa uma proposta de troca."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("DELETE FROM trocas WHERE id = ?", (troca_id,))
            await db.commit()

    async def pode_coletar(self, usuario_id):
        """Verifica se o usuário pode usar o comando /coletar."""
        async with aiosqlite.connect("eros.db") as db:
            cursor = await db.execute("SELECT ultimo_coletar FROM cooldowns WHERE usuario_id = ?", (usuario_id,))
            resultado = await cursor.fetchone()

        if not resultado or not resultado[0]:
            return True, None  # Nunca usou o comando antes

        ultimo_coletar = datetime.fromisoformat(resultado[0])
        tempo_restante = (ultimo_coletar + timedelta(hours=18)) - datetime.now()

        if tempo_restante > timedelta(0):
            return False, tempo_restante  # Ainda em cooldown
        else:
            return True, None  # Pode coletar

    async def atualizar_cooldown_coletar(self, usuario_id):
        """Atualiza o momento em que o usuário usou o comando /coletar."""
        async with aiosqlite.connect("eros.db") as db:
            await db.execute("""
                INSERT OR IGNORE INTO cooldowns (usuario_id, ultimo_coletar) VALUES (?, ?)
                ON CONFLICT(usuario_id) DO UPDATE SET ultimo_coletar = ?
            """, (usuario_id, datetime.now().isoformat(), datetime.now().isoformat()))
            await db.commit()

bot = ErosBot()

# Adição de personagem ao banco de dados
@bot.tree.command(name="adicionar_personagem", description="📝 Adicione um novo personagem.")
async def adicionar_personagem(interaction: discord.Interaction, nome: str, imagem_url: str):
    sucesso = await bot.adicionar_personagem(nome, imagem_url)
    if sucesso:
        await interaction.response.send_message(f"✅ **{nome}** foi adicionado ao banco de dados!")
    else:
        await interaction.response.send_message(f"⚠️ **{nome}** já existe no banco de dados!")

# Exclusão de personagem do banco de dados (apenas para o dono do bot)
@bot.tree.command(name="excluir_personagem", description="[Dono] Exclui um personagem do banco de dados.")
async def excluir_personagem(interaction: discord.Interaction, nome: str):
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    await bot.excluir_personagem(nome)
    await interaction.response.send_message(f"✅ **{nome}** foi excluído do banco de dados!")

# Consultar o perfil do personagem e conferir se ele esta casado (e com quem), solteiro ou se não existe. 
@bot.tree.command(name="consultar_personagem", description="🔍 Veja o perfil de um personagem.")
async def perfil_personagem(interaction: discord.Interaction, nome: str):
    async with aiosqlite.connect("eros.db") as db:
        cursor = await db.execute("SELECT nome, imagem FROM personagens WHERE LOWER(nome) = LOWER(?)", (nome,))
        personagem = await cursor.fetchone()

    if not personagem:
        await interaction.response.send_message("⚠️ Personagem não encontrado!")
        return

    dono_id = await bot.obter_dono_personagem(nome)
    dono_info = f"❤️ Em um relacionamento com <@{dono_id}>" if dono_id else "Pode ser conquistado"

    embed = discord.Embed(title=f"{personagem[0]}", color=discord.Color.pink())
    embed.set_image(url=personagem[1])
    embed.add_field(name="Status", value=dono_info, inline=False)

    await interaction.response.send_message(embed=embed)

# Fazer um personagem aleatório aparecer para tentativa de flerte
@bot.tree.command(name="paquerar", description="🏹 Tente conquistar um personagem aleatório!")
async def flerte(interaction: discord.Interaction):
    pode_paquerar, tempo_restante, tempo_restante_casamento = await bot.can_paquerar(interaction.user.id)
    if not pode_paquerar:
        if tempo_restante_casamento:
            horas, resto = divmod(tempo_restante_casamento.seconds, 3600)
            minutos, segundos = divmod(resto, 60)
            await interaction.response.send_message(f"⏳ Você só pode se casar novamente em {horas}h {minutos}m {segundos}s.", ephemeral=True)
        else:
            horas, resto = divmod(tempo_restante.seconds, 3600)
            minutos, segundos = divmod(resto, 60)
            await interaction.response.send_message(f"⏳ Você já usou o comando /paquerar 5 vezes. Tente novamente em {horas}h {minutos}m {segundos}s.", ephemeral=True)
        return

    async with aiosqlite.connect("eros.db") as db:
        cursor = await db.execute("SELECT nome, imagem FROM personagens WHERE conquistado = 0 ORDER BY RANDOM() LIMIT 1")
        personagem = await cursor.fetchone()

    if not personagem:
        await interaction.response.send_message("❌ Nenhum personagem na mira de Eros")
        return

    nome_personagem, imagem_url = personagem

    embed = discord.Embed(title="💖 Alvo na mira de Eros", description=f"{nome_personagem} apareceu!", color=discord.Color.pink())
    embed.set_image(url=imagem_url)

    await bot.update_cooldown(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=FlerteView(nome_personagem, interaction.user))

class FlerteView(discord.ui.View):
    def __init__(self, personagem, usuario):
        super().__init__()
        self.personagem = personagem
        self.usuario = usuario
        self.pressionado = False

    @discord.ui.button(label="🏹 Atirar", style=discord.ButtonStyle.primary)
    async def flertar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.usuario:
            await interaction.response.send_message("❌ Esse não é o seu encontro!", ephemeral=True)
            return
        
        if self.pressionado:
            await interaction.response.send_message("⚠️ Você já tentou conquistar esse amor", ephemeral=True)
            return

        # Verifica o cooldown de casamento
        pode_paquerar, _, tempo_restante_casamento = await bot.can_paquerar(interaction.user.id)
        if not pode_paquerar and tempo_restante_casamento:
            horas, resto = divmod(tempo_restante_casamento.seconds, 3600)
            minutos, segundos = divmod(resto, 60)
            await interaction.response.send_message(f"⏳ Você só pode se casar novamente em {horas}h {minutos}m {segundos}s.", ephemeral=True)
            return

        self.pressionado = True

        num_user = random.randint(1, 20)
        num_personagem = random.randint(1, 20) + 3  # Adiciona +3 de vantagem ao número do personagem

        if num_user >= num_personagem:
            await bot.adicionar_amor(interaction.user.id, self.personagem)
            resposta = f"💘 Eros acertou em cheio! Agora você esta casado com **{self.personagem}**!\n🎲 Eros tirou **{num_user}** e seu alvo **{num_personagem}**."
            await bot.update_cooldown(interaction.user.id, casou=True)
        else:
            resposta = f"💔 {self.personagem} esquivou, não foi dessa vez...\n🎲 Eros tirou **{num_user}** e seu alvo **{num_personagem}**."

        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(resposta)

# Divorciar de uma das suas paixões
@bot.tree.command(name="divorciar", description="💔 Libere um dos seus amores.")
async def divorciar(interaction: discord.Interaction, personagem: str):
    sucesso = await bot.liberar_personagem(interaction.user.id, personagem)
    if sucesso:
        await interaction.response.send_message(f"💔 Você se divorciou de **{personagem}**.")
    else:
        await interaction.response.send_message("❌ Você não pode se divorciar de um personagem que não te pertence!")

# Limpar todos os relacionamentos (apenas para o dono do bot)
@bot.tree.command(name="limpar_amores", description="[Dono] Limpa todos os relacionamentos.")
async def limpar_amores(interaction: discord.Interaction):
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    await bot.limpar_todos_amores()
    await interaction.response.send_message("✅ Todos os personagens sofreram divórcio e estão disponíveis novamente.")

# Listar os personagens conquistados pelo usuário (em partes de 15 em 15)
@bot.tree.command(name="meus_amores", description="💞 Veja a lista de personagens com quem você está casado.")
async def meus_amores(interaction: discord.Interaction):
    amores = await bot.listar_amores(interaction.user.id)
    if not amores:
        await interaction.response.send_message("💔 Você ainda não conquistou ninguém.")
        return

    # Divide a lista em partes de 15 personagens
    partes = [amores[i:i + 15] for i in range(0, len(amores), 15)]
    total_partes = len(partes)

    # Cria a view com botões de navegação
    view = AmoresView(partes, total_partes, interaction.user)

    # Envia a primeira parte
    lista = "\n".join(f"❤️ {nome}" for nome in partes[0])
    embed = discord.Embed(
        title="Seus amores",
        description=f"**Página 1 de {total_partes}**\n{lista}",
        color=discord.Color.pink()
    )
    await interaction.response.send_message(embed=embed, view=view)

class AmoresView(discord.ui.View):
    def __init__(self, partes, total_partes, usuario):
        super().__init__()
        self.partes = partes
        self.total_partes = total_partes
        self.pagina_atual = 0
        self.usuario = usuario

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.usuario:
            await interaction.response.send_message("❌ Esse não é o seu comando!", ephemeral=True)
            return

        self.pagina_atual = (self.pagina_atual - 1) % self.total_partes
        lista = "\n".join(f"❤️ {nome}" for nome in self.partes[self.pagina_atual])
        embed = discord.Embed(
            title="Seus amores",
            description=f"**Página {self.pagina_atual + 1} de {self.total_partes}**\n{lista}",
            color=discord.Color.pink()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.usuario:
            await interaction.response.send_message("❌ Esse não é o seu comando!", ephemeral=True)
            return

        self.pagina_atual = (self.pagina_atual + 1) % self.total_partes
        lista = "\n".join(f"❤️ {nome}" for nome in self.partes[self.pagina_atual])
        embed = discord.Embed(
            title="Seus amores",
            description=f"**Página {self.pagina_atual + 1} de {self.total_partes}**\n{lista}",
            color=discord.Color.pink()
        )
        await interaction.response.edit_message(embed=embed, view=self)

# Verificar saldo de Eritos
@bot.tree.command(name="saldo", description="💰 Veja quantos Eritos você possui.")
async def saldo(interaction: discord.Interaction):
    eritos = await bot.obter_eritos(interaction.user.id)
    await interaction.response.send_message(f"💰 Você possui **{eritos}** Eritos.")

# Adicionar ou remover Eritos (apenas para o dono do bot)
@bot.tree.command(name="gerenciar_eritos", description="[Dono] Adiciona ou remove Eritos de um usuário.")
async def gerenciar_eritos(interaction: discord.Interaction, usuario: discord.User, quantidade: int):
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    if quantidade > 0:
        await bot.adicionar_eritos(usuario.id, quantidade)
        await interaction.response.send_message(f"✅ **{quantidade}** Eritos foram adicionados ao saldo de {usuario.mention}.")
    else:
        await bot.remover_eritos(usuario.id, abs(quantidade))
        await interaction.response.send_message(f"🗑️ **{abs(quantidade)}** Eritos foram removidos do saldo de {usuario.mention}.")

# Oferecer um personagem em troca de Eritos
@bot.tree.command(name="oferecer_troca", description="🔄 Ofereça um personagem em troca de Eritos.")
async def oferecer_troca(interaction: discord.Interaction, personagem: str, destinatario: discord.User, quantidade_eritos: int):
    if destinatario.id == interaction.user.id:
        await interaction.response.send_message("❌ Você não pode oferecer um personagem para si mesmo!", ephemeral=True)
        return

    dono = await bot.obter_dono_personagem(personagem)
    if dono != interaction.user.id:
        await interaction.response.send_message("❌ Você não possui este personagem!", ephemeral=True)
        return

    eritos_destinatario = await bot.obter_eritos(destinatario.id)
    if eritos_destinatario < quantidade_eritos:
        await interaction.response.send_message(f"❌🤣 {destinatario.mention} não possui Eritos suficientes para a troca! POBRE!", ephemeral=True)
        return

    # Cria a troca e obtém o ID
    troca_id = await bot.criar_troca(interaction.user.id, personagem, destinatario.id, quantidade_eritos)

    # Envia a proposta com botões de aceitar/recusar
    view = TrocaView(troca_id, interaction.user.id, destinatario.id)
    await interaction.response.send_message(
        f"💌 {destinatario.mention}, você recebeu uma proposta de troca de {interaction.user.mention}:\n"
        f"**{personagem}** por **{quantidade_eritos} Eritos**.\n"
        f"Clique em ✅ para aceitar ou ✖️ para recusar.",
        view=view
    )

class TrocaView(discord.ui.View):
    def __init__(self, troca_id, ofertante_id, destinatario_id):
        super().__init__()
        self.troca_id = troca_id
        self.ofertante_id = ofertante_id
        self.destinatario_id = destinatario_id

    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.success)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.destinatario_id:
            await interaction.response.send_message("❌ Você não pode aceitar essa troca!", ephemeral=True)
            return

        sucesso = await bot.confirmar_troca(self.troca_id)
        if sucesso:
            await interaction.response.send_message("✅ Troca confirmada com sucesso!")
        else:
            await interaction.response.send_message("❌ A troca não pôde ser confirmada. Verifique se o personagem ainda está disponível.", ephemeral=True)

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.destinatario_id:
            await interaction.response.send_message("❌ Você não pode recusar essa troca!", ephemeral=True)
            return

        await bot.recusar_troca(self.troca_id)
        await interaction.response.send_message("❌ Troca recusada.")

# Coletar Eritos 
@bot.tree.command(name="coletar", description="💸 Colete seus Eritos (a cada 18 horas).")
async def coletar(interaction: discord.Interaction):
    pode_coletar, tempo_restante = await bot.pode_coletar(interaction.user.id)

    if not pode_coletar:
        horas, resto = divmod(tempo_restante.seconds, 3600)
        minutos, segundos = divmod(resto, 60)
        await interaction.response.send_message(
            f"⏳ Você já coletou seus Eritos. Tente novamente em {horas}h {minutos}m {segundos}s.",
            ephemeral=True
        )
        return

    eritos_ganhos = random.randint(0, 100)     # Gera uma quantidade aleatória de Eritos (0 a 100)

    await bot.adicionar_eritos(interaction.user.id, eritos_ganhos)     # Adiciona os Eritos ao usuário

    await bot.atualizar_cooldown_coletar(interaction.user.id)     # Atualiza o cooldown

    await interaction.response.send_message(
        f"💸 <@{interaction.user.id}> coletou **{eritos_ganhos}** Eritos! Volte em 18 horas para coletar mais."
    )

#Resetar Cooldowns
@bot.tree.command(name="resetar_cooldowns", description="[Dono] Reseta o cooldown de paquera de todos os usuários.")
async def resetar_cooldowns(interaction: discord.Interaction):
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    async with aiosqlite.connect("eros.db") as db:
        await db.execute("UPDATE cooldowns SET tentativas = 0, tempo = NULL")
        await db.commit()

    await interaction.response.send_message("✅ Cooldowns de paquera resetados para todos os usuários!")

@bot.tree.command(name="resetar_eritos", description="[Dono] Reseta os Eritos de todos os usuários para 0.")
async def resetar_eritos(interaction: discord.Interaction):
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    async with aiosqlite.connect("eros.db") as db:
        await db.execute("UPDATE moedas SET eritos = 0")
        await db.commit()

    await interaction.response.send_message("✅ Eritos de todos os usuários foram resetados para 0!")

@bot.tree.command(name="resetar_casamentos", description="[Dono] Reseta o cooldown de casamentos de todos os usuários.")
async def resetar_casamentos(interaction: discord.Interaction):
    # Verifica se o comando está sendo executado pelo dono do bot
    if interaction.user.id != SEU_ID:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        return

    async with aiosqlite.connect("eros.db") as db:
        # Reseta o cooldown de casamentos (define ultimo_casamento como NULL)
        await db.execute("UPDATE cooldowns SET ultimo_casamento = NULL")
        await db.commit()

    await interaction.response.send_message("✅ Cooldown de casamentos resetado para todos os usuários!")

#Rank
@bot.tree.command(name="rank", description="🏆 Exibe o top 10 usuários com mais Eritos.")
async def rank(interaction: discord.Interaction):
    async with aiosqlite.connect("eros.db") as db:
        # Consulta os 10 usuários com mais Eritos
        cursor = await db.execute("""
            SELECT usuario_id, eritos FROM moedas
            ORDER BY eritos DESC
            LIMIT 10
        """)
        top_usuarios = await cursor.fetchall()

    if not top_usuarios:
        await interaction.response.send_message("🏆 Nenhum usuário possui Eritos no momento.", ephemeral=True)
        return

    # Formata a lista de usuários
    lista_top = []
    for posicao, (usuario_id, eritos) in enumerate(top_usuarios, start=1):
        try:
            usuario = await bot.fetch_user(usuario_id)  # Obtém o nome do usuário pelo ID
            lista_top.append(f"{posicao}º: {usuario.name} - **{eritos}** Eritos")
        except discord.NotFound:
            # Se o usuário não for encontrado, exibe o ID
            lista_top.append(f"{posicao}º: Usuário {usuario_id} - **{eritos}** Eritos")

    # Cria uma embed para exibir o top 10
    embed = discord.Embed(
        title="🏆 Top 10 mais ricos",
        description="\n".join(lista_top),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

bot.run('SEU TOKEN') # Substitua pelo seu token
