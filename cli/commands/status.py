async def execute(bot, args):
    if args:
        print("Uso: status")
        return

    print("\n========== BISBO STATUS ==========")
    print(f"Bot: {bot.user}")
    print(f"ID: {bot.user.id if bot.user else 'Indisponível'}")
    print(f"Latência: {bot.latency * 1000:.0f} ms")
    print(f"Servidores: {len(bot.guilds)}")
    print(f"Usuários em cache: {len(bot.users)}")

    voice_connections = sum(1 for guild in bot.guilds if guild.voice_client is not None)

    print(f"Conexões de voz: {voice_connections}")
    print("==================================\n")
