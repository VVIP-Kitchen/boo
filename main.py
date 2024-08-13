from bot.bot import create_bot
from config import DISCORD_TOKEN

if __name__ == "__main__":
    bot = create_bot()
    bot.run(DISCORD_TOKEN)
