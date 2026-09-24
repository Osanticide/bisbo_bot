async def execute(bot, args):
    if len(args) < 2:
        print("Uso: say <canal_id> <mensagem>")
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        print("ID do canal inválido.")
        return

    channel = bot.get_channel(channel_id)

    if channel is None:
        print("Canal não encontrado ou não está disponível no cache.")
        return

    if not hasattr(channel, "send"):
        print("Esse canal não permite o envio de mensagens.")
        return

    message = " ".join(args[1:])

    try:
        await channel.send(message)
        print(f"Mensagem enviada para o canal {channel_id}.")
    except Exception as error:
        print(f"Falha ao enviar mensagem: {error}")
