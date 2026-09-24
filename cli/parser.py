import shlex

from cli.commands import say, voice, status


COMMANDS = {
    "say": say.execute,
    "voip": voice.execute,
    "status": status.execute,
}


def parse_command(line: str):
    try:
        parts = shlex.split(line)
    except ValueError as error:
        print(f"Erro ao interpretar comando: {error}")
        return None

    if not parts:
        return None

    command = parts[0].lower()
    args = parts[1:]

    return command, args


async def execute_command(bot, line: str):
    parsed = parse_command(line)

    if parsed is None:
        return

    command, args = parsed

    if command == "help":
        print(
            "\nComandos disponíveis:\n"
            "  help                     Mostra os comandos\n"
            "  status                   Mostra informações do bot\n"
            "  say <canal_id> <mensagem> Envia uma mensagem\n"
            "  voip <canal_id>          Conecta, desconecta ou troca de canal\n"
        )
        return

    handler = COMMANDS.get(command)

    if handler is None:
        print(f"Comando desconhecido: {command}")
        print("Digite 'help' para ver os comandos disponíveis.")
        return

    await handler(bot, args)
