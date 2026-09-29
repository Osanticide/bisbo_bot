import discord


class BaseView(discord.ui.View):
    """View base com controle de acesso ao usuário que a iniciou."""

    def __init__(self, interaction: discord.Interaction, *, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.author_id = interaction.user.id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Impede outros usuários de controlar esta interface."""

        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "🚫 Esta interface pertence a outro usuário.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self) -> None:
        """Desativa os controles quando a interface expira."""

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass


class Paginator(BaseView):
    """Paginação genérica reutilizável para listas de qualquer tipo."""

    def __init__(
        self,
        interaction: discord.Interaction,
        items: list,
        embed_factory,
        *,
        timeout: float = 60,
    ):
        if not items:
            raise ValueError("O paginator precisa receber pelo menos um item.")

        super().__init__(interaction, timeout=timeout)

        self.items = items
        self.embed_factory = embed_factory
        self.current_page = 0

        self._update_buttons()

    def _update_buttons(self) -> None:
        """Atualiza o estado dos botões conforme a quantidade de páginas."""

        has_multiple_pages = len(self.items) > 1

        self.previous_page.disabled = not has_multiple_pages
        self.next_page.disabled = not has_multiple_pages

    async def build_embed(self) -> discord.Embed:
        """Cria o embed da página atual."""

        result = self.embed_factory(
            self.items[self.current_page],
            self.current_page,
            len(self.items),
        )

        if hasattr(result, "__await__"):
            result = await result

        if not isinstance(result, discord.Embed):
            raise TypeError("embed_factory deve retornar discord.Embed.")

        return result

    async def update_message(self, interaction: discord.Interaction) -> None:
        """Atualiza a mensagem com a página atual."""

        self._update_buttons()

        embed = await self.build_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.secondary,
    )
    async def previous_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.current_page = (self.current_page - 1) % len(self.items)
        await self.update_message(interaction)

    @discord.ui.button(
        label="➡️",
        style=discord.ButtonStyle.secondary,
    )
    async def next_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.current_page = (self.current_page + 1) % len(self.items)
        await self.update_message(interaction)


__all__ = ["BaseView", "Paginator"]
