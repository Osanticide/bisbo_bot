"""
Testes integrados do Bisbo — use SOMENTE um banco PostgreSQL de testes.
Execute na raiz do projeto: python testar_economia.py
Configure BISBO_TEST_DATABASE_URL com a URL exclusiva do banco de testes.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

import asyncpg

from app.database.schema import PROFILE_TABLE_SQL
from app.database.profiles import ProfileRepository
from app.services.economy import EconomyError, to_money, validate_amount, format_money
from app.services.rewards import (
    REWARDS, RewardError, roll_reward, calculate_reward_xp,
    get_period_start, get_next_reward_time, BRASILIA,
)

DB_ENV = "BISBO_TEST_DATABASE_URL"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_pure_functions():
    check(to_money("12.349") == Decimal("12.34"), "to_money deve truncar centavos")
    check(validate_amount("0.01") == Decimal("0.01"), "mínimo válido")
    check(format_money("1234.5") == "1.234,50 CP", "formatação monetária")
    for value in (0, "-1", "0.009", float("1.2"), "NaN", "abc"):
        try:
            validate_amount(value)
        except EconomyError:
            pass
        else:
            raise AssertionError(f"validate_amount deveria rejeitar {value!r}")

    for kind, cfg in REWARDS.items():
        for _ in range(30):
            amount = roll_reward(kind)
            check(Decimal(cfg["minimum"]) <= amount <= Decimal(cfg["maximum"]),
                  f"reward {kind} fora dos limites")
            check(amount == amount.to_integral_value(), "reward deve ser inteiro em CP")
    check(calculate_reward_xp(Decimal("7.00")) == 1, "XP mínimo")
    check(calculate_reward_xp(Decimal("12.00")) == 3, "XP = CP/4 arredondado para baixo")

    now = datetime(2026, 9, 23, 15, 30, tzinfo=BRASILIA)
    check(get_period_start("daily", now).hour == 0, "início diário")
    check(get_period_start("weekly", now).weekday() == 6, "semana inicia domingo")
    check(get_period_start("monthly", now).day == 1, "início mensal")
    check(get_next_reward_time("daily", now).date() == (now + timedelta(days=1)).date(),
          "próximo daily")


async def test_database():
    dsn = os.getenv(DB_ENV)
    if not dsn:
        raise RuntimeError(
            f"Defina {DB_ENV} apontando para um BANCO DE TESTES separado. "
            "O script não usa DATABASE_URL por segurança."
        )
    dbname = urlparse(dsn).path.lstrip("/")
    if not dbname or "test" not in dbname.lower():
        raise RuntimeError("Por segurança, o nome do banco deve conter 'test'.")

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)
    repo = ProfileRepository(pool)
    uid = int(f"8{uuid.uuid4().int % 900000000000000000:018d}")
    uid2 = uid + 1
    ids = (uid, uid2)

    try:
        async with pool.acquire() as conn:
            await conn.execute(PROFILE_TABLE_SQL)

        # Perfil e saldos iniciais
        profile = await repo.get_or_create_profile(uid)
        check(profile["wallet"] == 0 and profile["bank"] == 0, "perfil inicial zerado")

        # Crédito de carteira para exercitar depósito/saque em perfil isolado
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET wallet=1000.00 WHERE user_id=$1", uid)
        result = await repo.deposit(uid, "250.00")
        check(result["wallet"] == Decimal("750.00"), "depósito: carteira")
        check(result["bank"] == Decimal("250.00"), "depósito: banco")
        result = await repo.withdraw(uid, "50.00")
        check(result["wallet"] == Decimal("800.00"), "saque: carteira")
        check(result["bank"] == Decimal("200.00"), "saque: banco")

        # Operação inválida não deve movimentar saldo
        before = await repo.get_balance(uid)
        try:
            await repo.withdraw(uid, "999999")
        except EconomyError:
            pass
        else:
            raise AssertionError("saque acima do saldo deveria falhar")
        after = await repo.get_balance(uid)
        check(before == after, "saque inválido alterou saldo")

        # Juros compostos: saldo de teste de 100.00, marco de 2 dias atrás
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE profiles SET bank=100.00,
                   bank_interest_at=(date_trunc('day', NOW() AT TIME ZONE 'America/Sao_Paulo')
                                     AT TIME ZONE 'America/Sao_Paulo') - interval '2 days'
                   WHERE user_id=$1""", uid
            )
        await repo.apply_bank_interest()
        row = await repo.get_profile(uid)
        check(Decimal(row["bank"]) == Decimal("102.01"),
              f"juros compostos de 2 dias esperados 102.01, recebido {row['bank']}")

        # Idempotência: nova chamada no mesmo dia não pode pagar novamente
        await repo.apply_bank_interest()
        row2 = await repo.get_profile(uid)
        check(Decimal(row2["bank"]) == Decimal("102.01"), "juros duplicados no mesmo dia")

        # Depósito com juros vencidos: juros liquidados antes de incorporar o novo depósito
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE profiles SET wallet=500.00, bank=100.00,
                   bank_interest_at=(date_trunc('day', NOW() AT TIME ZONE 'America/Sao_Paulo')
                                     AT TIME ZONE 'America/Sao_Paulo') - interval '2 days'
                   WHERE user_id=$1""", uid
            )
        await repo.deposit(uid, "50.00")
        row = await repo.get_profile(uid)
        check(Decimal(row["bank"]) == Decimal("152.01"),
              f"depósito deveria liquidar juros prévios e somar depósito; recebido {row['bank']}")

        # Rewards: resgate concede CP/XP e bloqueia segundo resgate no período
        period = get_period_start("daily", datetime.now(BRASILIA))
        amount = Decimal("20.00")
        reward = await repo.claim_reward(uid2, "daily", amount, 5, period)
        check(reward["amount"] == amount and reward["earned_xp"] == 5, "reward concedido")
        try:
            await repo.claim_reward(uid2, "daily", amount, 5, period)
        except RewardError:
            pass
        else:
            raise AssertionError("reward duplicado deveria ser bloqueado")
        prof2 = await repo.get_profile(uid2)
        check(Decimal(prof2["wallet"]) == amount, "saldo reward")
        check(prof2["xp"] == 5, "XP reward")

        print("  ✓ Integração PostgreSQL: perfil, depósito/saque, juros, idempotência e rewards")
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM profiles WHERE user_id = ANY($1::bigint[])", list(ids))
        await pool.close()


def main():
    print("Executando testes puros...")
    test_pure_functions()
    print("  ✓ Decimal, validações, formatação, rewards e períodos")
    print("Executando testes integrados...")
    asyncio.run(test_database())
    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFALHA: {exc}", file=sys.stderr)
        sys.exit(1)
