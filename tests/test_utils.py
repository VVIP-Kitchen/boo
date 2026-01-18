import json
import os
import sys
import types
import unittest
from datetime import datetime, timedelta

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
  sys.path.insert(0, SRC_PATH)

if "discord" not in sys.modules:
  discord_stub = types.ModuleType("discord")

  class Emoji:
    pass

  discord_stub.Emoji = Emoji
  sys.modules["discord"] = discord_stub

from utils.cache import ServerCache
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.llm_utils import has_vision_content, to_base64_data_uri
from utils.message_handler import prepare_chat_messages
from utils.singleton import Singleton
from utils.tool_executor import ToolExecutor


class TestLLMUtils(unittest.TestCase):
  def test_to_base64_data_uri(self):
    image_bytes = b"hello"
    self.assertEqual(
      to_base64_data_uri(image_bytes), "data:image/jpeg;base64,aGVsbG8="
    )

  def test_has_vision_content(self):
    messages = [
      {
        "content": [
          {"type": "text", "text": "hi"},
          {"type": "image_url", "image_url": {"url": "https://img"}},
        ]
      }
    ]
    self.assertTrue(has_vision_content(messages))
    self.assertFalse(has_vision_content([{ "content": "just text" }]))
    self.assertFalse(has_vision_content(None))


class TestMessageHandler(unittest.TestCase):
  def test_prepare_chat_messages_prompt(self):
    result = prepare_chat_messages(prompt="hello")
    self.assertEqual(result, [{"role": "user", "content": "hello"}])

  def test_prepare_chat_messages_messages_string(self):
    result = prepare_chat_messages(messages="hello")
    self.assertEqual(result, [{"role": "user", "content": "hello"}])

  def test_prepare_chat_messages_messages_list(self):
    messages = [{"role": "user", "content": "ready"}]
    self.assertEqual(prepare_chat_messages(messages=messages), messages)

  def test_prepare_chat_messages_with_image(self):
    image_bytes = b"image"
    result = prepare_chat_messages(prompt="describe", image=image_bytes)
    self.assertEqual(result[0]["role"], "user")
    content = result[0]["content"]
    self.assertEqual(content[0]["text"], "describe")
    self.assertEqual(
      content[1]["image_url"]["url"], to_base64_data_uri(image_bytes)
    )


class TestToolExecutor(unittest.TestCase):
  def setUp(self):
    self.executor = ToolExecutor(
      {
        "add": {
          "function": lambda x, y: {"sum": x + y},
        }
      }
    )

  def test_execute_tool_call_simple(self):
    result = json.loads(
      self.executor.execute_tool_call({"name": "add", "parameters": {"x": 2, "y": 3}})
    )
    self.assertEqual(result, {"sum": 5})

  def test_execute_tool_call_function_format(self):
    result = json.loads(
      self.executor.execute_tool_call(
        {"function": {"name": "add", "arguments": "{\"x\": 1, \"y\": 4}"}}
      )
    )
    self.assertEqual(result, {"sum": 5})

  def test_execute_tool_call_unknown(self):
    result = json.loads(self.executor.execute_tool_call({"name": "noop"}))
    self.assertIn("error", result)

  def test_image_result_helpers(self):
    success = {"status": "success", "image_data": "abc", "format": "jpg"}
    self.assertTrue(self.executor.is_image_generation_result("generate_image", success))
    self.assertEqual(
      self.executor.extract_image_data(success),
      {"data": "abc", "format": "jpg"},
    )


class TestServerCache(unittest.TestCase):
  def setUp(self):
    ServerCache._instance = None
    self.cache = ServerCache(ttl_minutes=1)
    self.cache.clear_all()

  def test_set_get_and_invalidate(self):
    self.cache.set_lore("guild", "lore")
    self.assertEqual(self.cache.get_lore("guild"), "lore")
    self.cache.invalidate_lore("guild")
    self.assertIsNone(self.cache.get_lore("guild"))

  def test_cleanup_expired_entries(self):
    expired_time = datetime.now() - timedelta(minutes=5)
    self.cache._lore_cache["expired"] = ("old", expired_time)
    self.cache._lore_cache["active"] = (
      "new",
      datetime.now() + timedelta(minutes=5),
    )
    removed = self.cache.cleanup_expired()
    self.assertEqual(removed, 1)
    self.assertNotIn("expired", self.cache._lore_cache)

  def test_cache_stats(self):
    self.cache._lore_cache["active"] = (
      "new",
      datetime.now() + timedelta(minutes=5),
    )
    self.cache._lore_cache["expired"] = (
      "old",
      datetime.now() - timedelta(minutes=5),
    )
    stats = self.cache.get_cache_stats()
    self.assertEqual(stats["total_entries"], 2)
    self.assertEqual(stats["active_entries"], 1)
    self.assertEqual(stats["expired_entries"], 1)


class ExampleSingleton(metaclass=Singleton):
  def __init__(self, value):
    self.value = value


class TestSingleton(unittest.TestCase):
  def test_singleton_returns_same_instance(self):
    first = ExampleSingleton(1)
    second = ExampleSingleton(2)
    self.assertIs(first, second)
    self.assertEqual(first.value, 1)


class FakeEmoji:
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return f"<:{self.name}:123>"


class TestEmojiUtils(unittest.TestCase):
  def test_replace_emojis(self):
    custom = {"wave": FakeEmoji("wave")}
    result = replace_emojis("Hello :wave:", custom)
    self.assertEqual(result, "Hello <:wave:123>")

  def test_replace_stickers(self):
    text, stickers = replace_stickers("Hi &sparkles;123& there &wow;456&")
    self.assertEqual(text, "Hi  there ")
    self.assertEqual(stickers, ["123", "456"])


if __name__ == "__main__":
  unittest.main()
