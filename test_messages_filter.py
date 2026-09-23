import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.cogs.messages import MessageXP


class TestMessageFilter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = SimpleNamespace(
            command_prefix="!",
            xp_service=SimpleNamespace(
                process_message=AsyncMock(
                    return_value={
                        "levels_gained": 0,
                        "level": 1,
                    }
                )
            ),
        )

        self.cog = MessageXP(self.bot)

    def make_message(
        self,
        *,
        bot=False,
        guild=True,
        content="Olá",
        attachments=None,
    ):
        return SimpleNamespace(
            author=SimpleNamespace(
                bot=bot,
                id=123,
                mention="<@123>",
            ),
            guild=object() if guild else None,
            content=content,
            attachments=attachments or [],
            channel=SimpleNamespace(send=AsyncMock()),
        )

    async def test_mensagem_valida_conta(self):
        message = self.make_message()

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_awaited_once_with(123)

    async def test_mensagem_de_bot_e_ignorada(self):
        message = self.make_message(bot=True)

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_not_awaited()

    async def test_mensagem_privada_e_ignorada(self):
        message = self.make_message(guild=False)

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_not_awaited()

    async def test_comando_tradicional_e_ignorado(self):
        message = self.make_message(content="!ping")

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_not_awaited()

    async def test_mensagem_vazia_e_ignorada(self):
        message = self.make_message(content="   ")

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_not_awaited()

    async def test_anexo_sem_texto_conta(self):
        message = self.make_message(
            content="",
            attachments=[object()],
        )

        await self.cog.on_message(message)

        self.bot.xp_service.process_message.assert_awaited_once_with(123)


if __name__ == "__main__":
    unittest.main(verbosity=2)
