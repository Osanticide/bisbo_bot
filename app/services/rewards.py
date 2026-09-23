from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from zoneinfo import ZoneInfo
import random


BRASILIA = ZoneInfo("America/Sao_Paulo")

REWARDS = {
    "daily": {
        "name": "Diária", "minimum": 5, "maximum": 500,
        "cooldown": "daily_reward_at",
    },
    "weekly": {
        "name": "Semanal", "minimum": 200, "maximum": 1000,
        "cooldown": "weekly_reward_at",
    },
    "monthly": {
        "name": "Mensal", "minimum": 1000, "maximum": 15000,
        "cooldown": "monthly_reward_at",
    },
}

# Beta(a=1, b) concentra os resultados perto do mínimo.
# Quanto maior b, mais raros ficam os valores altos.
REWARD_DISTRIBUTION_BETA = {
    "daily": 2,
    "weekly": 4,
    "monthly": 12,
}


class RewardError(Exception):
    """Erro relacionado ao sistema de recompensas."""


def get_period_start(reward_type: str, now: datetime) -> datetime:
    now = now.astimezone(BRASILIA)
    if reward_type == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if reward_type == "weekly":
        sunday = now - timedelta(days=(now.weekday() + 1) % 7)
        return sunday.replace(hour=0, minute=0, second=0, microsecond=0)
    if reward_type == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise RewardError("Tipo de recompensa inválido.")


def roll_reward(reward_type: str) -> Decimal:
    config = REWARDS.get(reward_type)
    if config is None:
        raise RewardError("Tipo de recompensa inválido.")

    skew = random.betavariate(1, REWARD_DISTRIBUTION_BETA[reward_type])
    span = config["maximum"] - config["minimum"]
    amount = config["minimum"] + int(skew * (span + 1))
    amount = min(amount, config["maximum"])
    return Decimal(amount).quantize(Decimal("0.01"))


def calculate_reward_xp(amount: Decimal) -> int:
    xp = (amount / Decimal("4")).to_integral_value(rounding=ROUND_FLOOR)
    return max(1, int(xp))


def get_next_reward_time(reward_type: str, now: datetime) -> datetime:
    now = now.astimezone(BRASILIA)
    if reward_type == "daily":
        return (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    if reward_type == "weekly":
        days_until_sunday = (6 - now.weekday()) % 7 or 7
        return (now + timedelta(days=days_until_sunday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    if reward_type == "monthly":
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        return next_month.replace(hour=0, minute=0, second=0, microsecond=0)
    raise RewardError("Tipo de recompensa inválido.")
