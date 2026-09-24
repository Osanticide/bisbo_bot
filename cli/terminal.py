import asyncio
import threading

from cli.parser import execute_command


class TerminalCLI:
    def __init__(self, bot):
        self.bot = bot
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="bisbo-cli",
        )

        self.thread.start()

    def stop(self):
        self.running = False

    def _input_loop(self):
        print("\nCLI administrativa do Bisbo iniciada.")
        print("Digite 'help' para ver os comandos.\n")

        while self.running:
            try:
                line = input("bisbo> ")
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

            if not line.strip():
                continue

            future = asyncio.run_coroutine_threadsafe(
                execute_command(self.bot, line),
                self.bot.loop,
            )

            try:
                future.result(timeout=60)
            except Exception as error:
                print(f"Erro na CLI: {error}")
