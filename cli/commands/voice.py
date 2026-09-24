async def execute(bot, args):
    if len(args) != 1:
        print("Uso: voip <canal_id>")
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

    if not hasattr(channel, "connect"):
        print("O ID informado não corresponde a um canal de voz.")
        return

    voice_client = channel.guild.voice_client

    try:
        if voice_client is not None:
            if voice_client.channel.id == channel_id:
                await voice_client.disconnect()
                print("Bisbo desconectado do canal de voz.")
                return

            await voice_client.move_to(channel)
            print(f"Bisbo transferido para o canal {channel.name}.")
            return

        await channel.connect()
        print(f"Bisbo conectado ao canal {channel.name}.")

    except Exception as error:
        print(f"Falha ao executar comando de voz: {error}")
