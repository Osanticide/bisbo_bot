import asyncpg

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.services.economy import (
    CENT,
    ZERO,
    EconomyError,
    validate_amount,
)


class ProfileRepository:
    """Executa operações relacionadas aos perfis e à economia."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _settle_bank_interest(self, connection, profile, today_start, brasilia):
        """Liquida juros vencidos sobre o saldo existente antes da movimentação."""
        marker = profile["bank_interest_at"]
        balance = Decimal(profile["bank"])

        if marker is None:
            await connection.execute(
                "UPDATE profiles SET bank_interest_at = $2 WHERE user_id = $1;",
                profile["user_id"],
                today_start,
            )
            return balance, Decimal("0.00"), today_start

        marker_local = marker.astimezone(brasilia)
        days_due = (today_start.date() - marker_local.date()).days
        if days_due <= 0:
            return balance, Decimal("0.00"), marker

        interest_total = Decimal("0.00")
        for _ in range(days_due):
            daily_interest = (balance * Decimal("0.01")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            balance += daily_interest
            interest_total += daily_interest

        await connection.execute(
            """UPDATE profiles
               SET bank = $2, bank_interest_at = $3
               WHERE user_id = $1;""",
            profile["user_id"],
            balance,
            today_start,
        )
        return balance, interest_total, today_start

    async def get_profile(self, user_id: int):
        query = "SELECT * FROM profiles WHERE user_id = $1;"
        return await self.pool.fetchrow(query, user_id)

    async def get_or_create_profile(self, user_id: int):
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO profiles (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING;
                """,
                user_id,
            )

            return await connection.fetchrow(
                "SELECT * FROM profiles WHERE user_id = $1;",
                user_id,
            )

    async def register_valid_message(self, user_id: int) -> dict:
        """
        Registra uma mensagem válida.
        A cada 5 mensagens, concede 10 XP.
        """
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO profiles (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    user_id,
                )

                row = await connection.fetchrow(
                    """
                    SELECT level, xp, message_count
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE;
                    """,
                    user_id,
                )

                count = row["message_count"] + 1
                earned_xp = 0
                levels_gained = 0
                level = row["level"]
                xp = row["xp"]

                if count >= 5:
                    count = 0
                    earned_xp = 10
                    xp += earned_xp

                    while xp >= 20 * level:
                        xp -= 20 * level
                        level += 1
                        levels_gained += 1

                await connection.execute(
                    """
                    UPDATE profiles
                    SET message_count = $2,
                        level = $3,
                        xp = $4,
                        updated_at = NOW()
                    WHERE user_id = $1;
                    """,
                    user_id,
                    count,
                    level,
                    xp,
                )

        return {
            "message_count": count,
            "earned_xp": earned_xp,
            "level": level,
            "xp": xp,
            "levels_gained": levels_gained,
        }

    async def get_balance(self, user_id: int):
        """Retorna os saldos da carteira e do banco."""
        profile = await self.get_or_create_profile(user_id)

        return {
            "wallet": Decimal(profile["wallet"]),
            "bank": Decimal(profile["bank"]),
        }

    async def deposit(
        self,
        user_id: int,
        amount: Decimal | int | str,
    ):
        """Transfere CP da carteira para o banco."""
        amount = validate_amount(amount)

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO profiles (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    user_id,
                )

                profile = await connection.fetchrow(
                    """
                    SELECT user_id, wallet, bank, bank_interest_at
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE;
                    """,
                    user_id,
                )

                brasilia = ZoneInfo("America/Sao_Paulo")
                now = datetime.now(timezone.utc).astimezone(brasilia)
                today_start = datetime.combine(now.date(), time.min, tzinfo=brasilia)
                bank, _, _ = await self._settle_bank_interest(
                    connection, profile, today_start, brasilia
                )
                wallet = Decimal(profile["wallet"])

                if wallet < amount:
                    raise EconomyError("Você não possui CP suficientes na carteira.")

                await connection.execute(
                    """
                    UPDATE profiles
                    SET wallet = wallet - $2,
                        bank = $3,
                        updated_at = NOW()
                    WHERE user_id = $1;
                    """,
                    user_id,
                    amount,
                    bank + amount,
                )

                return {
                    "wallet": wallet - amount,
                    "bank": bank + amount,
                    "amount": amount,
                }

    async def withdraw(
        self,
        user_id: int,
        amount: Decimal | int | str,
    ):
        """Transfere CP do banco para a carteira."""
        amount = validate_amount(amount)

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO profiles (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    user_id,
                )

                profile = await connection.fetchrow(
                    """
                    SELECT user_id, wallet, bank, bank_interest_at
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE;
                    """,
                    user_id,
                )

                brasilia = ZoneInfo("America/Sao_Paulo")
                now = datetime.now(timezone.utc).astimezone(brasilia)
                today_start = datetime.combine(now.date(), time.min, tzinfo=brasilia)
                bank, _, _ = await self._settle_bank_interest(
                    connection, profile, today_start, brasilia
                )

                if bank < amount:
                    raise EconomyError("Você não possui CP suficientes no banco.")

                await connection.execute(
                    """
                    UPDATE profiles
                    SET bank = $3,
                        wallet = wallet + $2,
                        updated_at = NOW()
                    WHERE user_id = $1;
                    """,
                    user_id,
                    amount,
                    bank - amount,
                )

                return {
                    "wallet": Decimal(profile["wallet"]) + amount,
                    "bank": bank - amount,
                    "amount": amount,
                }

    async def claim_reward(
        self,
        user_id: int,
        reward_type: str,
        amount,
        earned_xp: int,
        period_start,
    ) -> dict:
        """
        Concede uma recompensa de forma transacional.

        Impede resgates duplicados no mesmo período e atualiza:
        - saldo da carteira;
        - XP e nível;
        - data do último resgate.
        """

        from app.services.rewards import REWARDS, RewardError

        if reward_type not in REWARDS:
            raise RewardError("Tipo de recompensa inválido.")

        cooldown_column = REWARDS[reward_type]["cooldown"]

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO profiles (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    user_id,
                )

                profile = await connection.fetchrow(
                    """
                    SELECT level, xp, wallet, daily_reward_at,
                           weekly_reward_at, monthly_reward_at
                    FROM profiles
                    WHERE user_id = $1
                    FOR UPDATE;
                    """,
                    user_id,
                )

                last_claim = profile[cooldown_column]

                if last_claim is not None and last_claim >= period_start:
                    raise RewardError("Você já resgatou essa recompensa neste período.")

                level = profile["level"]
                xp = profile["xp"]

                xp += earned_xp
                levels_gained = 0

                while xp >= 20 * level:
                    xp -= 20 * level
                    level += 1
                    levels_gained += 1

                await connection.execute(
                    f"""
                    UPDATE profiles
                    SET wallet = wallet + $2,
                        level = $3,
                        xp = $4,
                        {cooldown_column} = NOW(),
                        updated_at = NOW()
                    WHERE user_id = $1;
                    """,
                    user_id,
                    amount,
                    level,
                    xp,
                )

        return {
            "amount": amount,
            "earned_xp": earned_xp,
            "level": level,
            "xp": xp,
            "levels_gained": levels_gained,
        }

    async def apply_bank_interest(self) -> dict:
        """Aplica 1% por dia completo, capitalizado e sem retroagir sobre depósitos."""
        brasilia = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(timezone.utc).astimezone(brasilia)
        today_start = datetime.combine(now.date(), time.min, tzinfo=brasilia)
        processed = 0
        total_interest = Decimal("0.00")

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                profiles = await connection.fetch(
                    """SELECT user_id, bank, bank_interest_at
                       FROM profiles
                       WHERE bank_interest_at IS NULL OR bank_interest_at < $1
                       FOR UPDATE;""",
                    today_start,
                )
                for profile in profiles:
                    _, interest, _ = await self._settle_bank_interest(
                        connection, profile, today_start, brasilia
                    )
                    if profile["bank_interest_at"] is not None and interest > 0:
                        processed += 1
                        total_interest += interest

        return {"profiles_processed": processed, "interest_paid": total_interest}
