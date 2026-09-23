from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from zoneinfo import ZoneInfo
import random


BRASILIA = ZoneInfo("America/Sao_Paulo")


REWARDS = {
    "daily": {
        "name": "Diária",
        "minimum": 5,
        "maximum": 500,
        "cooldown": "daily_reward_at",
    },
    "weekly": {
        "name": "Semanal",
        "minimum": 200,
        "maximum": 1000,
        "cooldown": "weekly_reward_at",
    },
    "monthly": {
        "name": "Mensal",
        "minimum": 1000,
        "maximum": 15000,
        "cooldown": "monthly_reward_at",
    },
}


class RewardError(Exception):
    """Erro relacionado ao sistema de recompensas."""


def get_period_start(reward_type: str, now: datetime) -> datetime:
    """Retorna o início do período atual no horário de Brasília."""

    now = now.astimezone(BRASILIA)

    if reward_type == "daily":
        return now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if reward_type == "weekly":
        # Domingo é o primeiro dia da semana.
        sunday = now - timedelta(days=(now.weekday() + 1) % 7)

        return sunday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if reward_type == "monthly":
        return now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    raise RewardError("Tipo de recompensa inválido.")


def roll_reward(reward_type: str) -> Decimal:
    """Sorteia uma recompensa, favorecendo valores menores."""

    config = REWARDS.get(reward_type)

    if config is None:
        raise RewardError("Tipo de recompensa inválido.")

    # Distribuição triangular favorece valores próximos ao mínimo.
    amount = random.triangular(
        config["minimum"],
        config["maximum"],
        config["minimum"],
    )

    # Recompensas inteiras em CP.
    amount = int(amount)

    return Decimal(amount).quantize(Decimal("0.01"))


def calculate_reward_xp(amount: Decimal) -> int:
    """Converte a recompensa em XP de perfil."""

    xp = (amount / Decimal("4")).to_integral_value(rounding=ROUND_FLOOR)

    return max(1, int(xp))


def get_next_reward_time(
    reward_type: str,
    now: datetime,
) -> datetime:
    """Calcula quando o próximo resgate estará disponível."""

    now = now.astimezone(BRASILIA)

    if reward_type == "daily":
        next_day = now + timedelta(days=1)

        return next_day.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if reward_type == "weekly":
        days_until_sunday = (6 - now.weekday()) % 7

        if days_until_sunday == 0:
            days_until_sunday = 7

        next_sunday = now + timedelta(days=days_until_sunday)

        return next_sunday.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    if reward_type == "monthly":
        if now.month == 12:
            next_month = now.replace(
                year=now.year + 1,
                month=1,
                day=1,
            )
        else:
            next_month = now.replace(
                month=now.month + 1,
                day=1,
            )

        return next_month.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    raise RewardError("Tipo de recompensa inválido.")
