import logging
from typing import Any


def setup_logger() -> logging.Logger:
  """
  Set up and configure a logger for the Discord bot.

  This function creates a logger with the name "discord_bot", sets its
  level to INFO, and adds a StreamHandler with a specific format.

  Returns:
      logging.Logger: A configured logger instance.
  """

  logger = logging.getLogger("discord_bot")
  logger.setLevel(logging.INFO)
  handler = logging.StreamHandler()
  formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  return logger


### Create a global logger instance
logger: Any = setup_logger()
