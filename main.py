from bot.bot import DiscordBot


def main() -> None:
  """
  Main entry point for the Discord bot.
  Initializes and runs the DiscordBot instance.
  """
  bot = DiscordBot()
  bot.run()


if __name__ == "__main__":
  main()
