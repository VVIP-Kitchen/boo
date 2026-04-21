from temporalio import activity

from services.db_service import DBService
from activities.models import TokenUsageInput


@activity.defn
def fetch_prompt(server_id: str) -> str:
  result = DBService().fetch_prompt(server_id)
  return (result or {}).get("system_prompt", "") or ""


@activity.defn
def get_chat_history(server_id: str) -> list:
  return DBService().get_chat_history(server_id) or []


@activity.defn
def update_chat_history(server_id: str, messages: list) -> bool:
  return DBService().update_chat_history(server_id, messages)


@activity.defn
def delete_chat_history(server_id: str) -> bool:
  return DBService().delete_chat_history(server_id)


@activity.defn
def get_memories(server_id: str, author_id: str) -> list:
  return DBService().get_memories(server_id, author_id) or []


@activity.defn
def store_token_usage(payload: TokenUsageInput) -> None:
  DBService().store_token_usage(
    {
      "message_id": payload.message_id,
      "guild_id": payload.guild_id,
      "author_id": payload.author_id,
      "input_tokens": payload.input_tokens,
      "output_tokens": payload.output_tokens,
    }
  )
