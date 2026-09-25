import discord
from typing import List, Any, Callable, Optional, Tuple

# --- CLASSE BASE (O Cérebro) ---
# Esta classe garante que apenas quem usou o comando pode interagir com os botões
class CindyBaseView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.author = interaction.user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("🚫 Esta interface pertence a outro usuário!", ephemeral=True)
            return False
        return True

# --- CLASSE DE NAVEGAÇÃO (As Setas) ---
# Ela herda da Base e foca apenas em passar páginas
class Paginator(CindyBaseView):
    def __init__(
        self, 
        interaction: discord.Interaction, 
        items: List[Any], 
        embed_factory: Callable[[Any, int, int], Any]
    ):
        super().__init__(interaction)
        self.items = items
        self.embed_factory = embed_factory # Função que gera o design da página
        self.current_page = 0

    async def update_view(self, interaction: discord.Interaction):
        # A 'fábrica' devolve o embed e um possível arquivo (imagem)
        result = await self.embed_factory(self.items[self.current_page], self.current_page, len(self.items))
        
        # Tratamento flexível: aceita (embed) ou (embed, file)
        if isinstance(result, tuple):
            embed, file = result
        else:
            embed, file = result, None

        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.items)
        await self.update_view(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.items)
        await self.update_view(interaction)