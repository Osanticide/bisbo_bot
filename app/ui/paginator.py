import discord
from collections.abc import Awaitable, Callable, Sequence
from typing import Any


EmbedFactory = Callable[
    [Any, int, int],
    Awaitable[discord.Embed],
]


class BaseView(discord.ui.View):
    """View base com controle do usuário que iniciou a interface."""

    def __init__(
        self,
        interaction: discord.Interaction,
        timeout: float = 60,
    ):
        super().__init__(timeout=timeout)
        self.author_id = interaction.user.id

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "🚫 Esta interface pertence a outro usuário.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class Paginator(BaseView):
    """Paginator reutilizável para interfaces baseadas em embeds."""

    def __init__(
        self,
        interaction: discord.Interaction,
        items: Sequence[Any],
        embed_factory: EmbedFactory,
        timeout: float = 60,
    ):
        super().__init__(
            interaction=interaction,
            timeout=timeout,
        )

        self.items = list(items)
        self.embed_factory = embed_factory
        self.current_page = 0

        self._update_buttons()

    def _update_buttons(self):
        has_pages = len(self.items) > 1

        self.previous_page.disabled = not has_pages
        self.next_page.disabled = not has_pages

    async def build_embed(self) -> discord.Embed:
        return await self.embed_factory(
            self.items[self.current_page],
            self.current_page,
            len(self.items),
        )

    async def update_message(
        self,
        interaction: discord.Interaction,
    ):
        embed = await self.build_embed()

        self._update_buttons()

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
