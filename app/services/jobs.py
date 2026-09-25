from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


BASE_CP = Decimal("1200")
LEVEL_MULTIPLIER = Decimal("1.15")
MILESTONE_MULTIPLIER = Decimal("1.25")

PROFESSIONAL_XP_RATE = Decimal("0.20")
PROFILE_XP_RATE = Decimal("0.10")

WORK_COOLDOWN = timedelta(hours=4)
MINIMUM_HIRE_TIME = timedelta(hours=24)

CENT = Decimal("0.01")


class JobError(Exception):
    """Erro relacionado ao sistema de empregos."""


class JobCooldownError(JobError):
    """Tentativa de trabalhar durante o cooldown."""

    def __init__(self, retry_at: datetime):
        self.retry_at = retry_at
        super().__init__("O trabalho ainda está em cooldown.")


def calculate_work_cp(coefficient: Decimal, level: int) -> Decimal:
    """
    Calcula o CP recebido por um trabalho.

    CP = 1200 × coeficiente × 1,15^(nível - 1)
         × 1,25^floor((nível - 1) / 5)
    """

    level_index = level - 1

    cp = (
        BASE_CP
        * coefficient
        * (LEVEL_MULTIPLIER**level_index)
        * (MILESTONE_MULTIPLIER ** (level_index // 5))
    )

    return cp.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_professional_xp(cp: Decimal) -> int:
    """Calcula o XP profissional recebido pelo trabalho."""

    return int((cp * PROFESSIONAL_XP_RATE).to_integral_value(rounding=ROUND_DOWN))


def calculate_profile_xp(cp: Decimal) -> int:
    """Calcula o XP de perfil recebido pelo trabalho."""

    return int((cp * PROFILE_XP_RATE).to_integral_value(rounding=ROUND_DOWN))


def xp_required_for_level(level: int) -> int:
    """Retorna o XP necessário para subir do nível atual."""

    return 1000 * level


def apply_job_xp(level: int, xp: int, earned_xp: int) -> dict:
    """
    Aplica XP profissional e processa todos os níveis alcançados.
    """

    total_xp = xp + earned_xp
    levels_gained = 0

    while total_xp >= xp_required_for_level(level):
        total_xp -= xp_required_for_level(level)
        level += 1
        levels_gained += 1

    return {
        "level": level,
        "xp": total_xp,
        "levels_gained": levels_gained,
    }


def apply_profile_xp(level: int, xp: int, earned_xp: int) -> dict:
    """
    Aplica XP de perfil usando a progressão já existente:
    XP necessário = 20 × nível.
    """

    total_xp = xp + earned_xp
    levels_gained = 0

    while total_xp >= 20 * level:
        total_xp -= 20 * level
        level += 1
        levels_gained += 1

    return {
        "level": level,
        "xp": total_xp,
        "levels_gained": levels_gained,
    }


def cooldown_remaining(last_work_at: datetime) -> timedelta:
    """Retorna quanto tempo falta para o próximo trabalho."""

    now = datetime.now(timezone.utc)
    retry_at = last_work_at + WORK_COOLDOWN

    return max(retry_at - now, timedelta(0))
