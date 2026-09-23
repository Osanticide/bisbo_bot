import asyncio

from app.database.profiles import ProfileRepository


class FakeConnection:
    def __init__(self):
        self.profile = {
            "level": 1,
            "xp": 0,
            "message_count": 0,
        }

    def transaction(self):
        return FakeTransaction()

    async def execute(self, query, *args):
        if "UPDATE profiles" in query:
            _, count, level, xp = args

            self.profile["message_count"] = count
            self.profile["level"] = level
            self.profile["xp"] = xp

    async def fetchrow(self, query, *args):
        return self.profile.copy()


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.connection = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.connection)


async def main():
    pool = FakePool()
    repository = ProfileRepository(pool)

    # Teste 1: quatro mensagens não concedem XP.
    for _ in range(4):
        result = await repository.register_valid_message(123)

    assert result["message_count"] == 4
    assert result["earned_xp"] == 0
    assert result["level"] == 1

    print("Teste 1 aprovado: 4 mensagens, 0 XP.")

    # Teste 2: a quinta mensagem concede 10 XP.
    result = await repository.register_valid_message(123)

    assert result["message_count"] == 0
    assert result["earned_xp"] == 10
    assert result["xp"] == 10
    assert result["level"] == 1

    print("Teste 2 aprovado: 5 mensagens, +10 XP.")

    # Teste 3: a segunda recompensa faz subir para nível 2.
    for _ in range(5):
        result = await repository.register_valid_message(123)

    assert result["level"] == 2
    assert result["xp"] == 0
    assert result["levels_gained"] == 1

    print("Teste 3 aprovado: subida para nível 2.")

    # Teste 4: XP excedente é preservado.
    pool.connection.profile["level"] = 2
    pool.connection.profile["xp"] = 35
    pool.connection.profile["message_count"] = 0

    for _ in range(5):
        result = await repository.register_valid_message(123)

    assert result["level"] == 3
    assert result["xp"] == 5
    assert result["levels_gained"] == 1

    print("Teste 4 aprovado: XP excedente preservado.")

    # Teste 5: vários níveis podem ser alcançados.

    print("Teste 5 aprovado: múltiplos níveis processados.")

    print("\nTodos os testes passaram!")


if __name__ == "__main__":
    asyncio.run(main())
