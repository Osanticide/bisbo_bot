from decimal import Decimal, InvalidOperation, ROUND_DOWN


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class EconomyError(Exception):
    """Erro esperado em uma operação econômica."""


def to_money(value: Decimal | int | str) -> Decimal:
    """
    Converte um valor para Decimal com duas casas decimais.

    Não aceita float para evitar imprecisão monetária.
    """
    if isinstance(value, float):
        raise EconomyError("Valores monetários não podem ser float.")

    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise EconomyError("Valor monetário inválido.")

    if not amount.is_finite():
        raise EconomyError("O valor precisa ser finito.")

    return amount.quantize(CENT, rounding=ROUND_DOWN)


def validate_amount(value: Decimal | int | str) -> Decimal:
    """Valida um valor positivo de pelo menos 0,01 CP."""
    amount = to_money(value)

    if amount < CENT:
        raise EconomyError("O valor mínimo é 0,01 CP.")

    return amount


def format_money(value: Decimal | int | str) -> str:
    """Formata um valor monetário com duas casas decimais."""
    amount = to_money(value)

    formatted = f"{amount:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{formatted} CP"
