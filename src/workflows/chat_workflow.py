from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
  from activities import discord_rest, llm, manager
  from activities.models import (
    ChatRequest,
    SendResponseInput,
    TokenUsageInput,
  )
  from utils.config import CONTEXT_LIMIT


EYES = "\U0001f440"
CROSS = "\u274c"

_short_retry = RetryPolicy(
  initial_interval=timedelta(seconds=1),
  backoff_coefficient=2.0,
  maximum_interval=timedelta(seconds=10),
  maximum_attempts=3,
)

_llm_retry = RetryPolicy(
  initial_interval=timedelta(seconds=2),
  backoff_coefficient=2.0,
  maximum_interval=timedelta(seconds=30),
  maximum_attempts=4,
)


@workflow.defn
class BooChatWorkflow:
  """End-to-end Discord message handler. Replaces the old in-bot blocking flow."""

  @workflow.run
  async def run(self, req: ChatRequest) -> None:
    await self._safe_react(req, EYES)

    try:
      if req.is_reset:
        await workflow.execute_activity(
          manager.delete_chat_history,
          req.server_id,
          start_to_close_timeout=timedelta(seconds=10),
          retry_policy=_short_retry,
        )
        await workflow.execute_activity(
          discord_rest.send_message,
          args=[req.channel_id, "Context reset! Starting a new conversation. \U0001f44b", None],
          start_to_close_timeout=timedelta(seconds=15),
          retry_policy=_short_retry,
        )
        return

      lore, history, memories = await self._gather_context(req)

      llm_input = llm.AgenticChatInput(
        request=req,
        lore=lore,
        history=history,
        memories=memories,
      )
      result = await workflow.execute_activity(
        llm.run_agentic_chat,
        llm_input,
        start_to_close_timeout=timedelta(minutes=5),
        retry_policy=_llm_retry,
      )

      await workflow.execute_activity(
        discord_rest.send_response,
        SendResponseInput(
          channel_id=req.channel_id,
          reply_to=req.message_id,
          content=result.response_text,
          sticker_ids=[],
          generated_images=result.generated_images,
        ),
        start_to_close_timeout=timedelta(minutes=2),
        retry_policy=_short_retry,
      )

      new_history = history + result.appended_messages
      if len(new_history) > CONTEXT_LIMIT:
        new_history = new_history[-CONTEXT_LIMIT:]

      await workflow.execute_activity(
        manager.update_chat_history,
        args=[req.server_id, new_history],
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=_short_retry,
      )

      await workflow.execute_activity(
        manager.store_token_usage,
        TokenUsageInput(
          message_id=req.message_id,
          guild_id=req.server_id,
          author_id=req.author_id,
          input_tokens=result.usage.prompt_tokens,
          output_tokens=result.usage.total_tokens,
        ),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=_short_retry,
      )

    except Exception as e:
      workflow.logger.error(f"BooChatWorkflow failed for message {req.message_id}: {e}")
      await self._safe_react(req, CROSS)
      await workflow.execute_activity(
        discord_rest.send_message,
        args=[
          req.channel_id,
          "I encountered an error while processing your message. Please try again later!",
          req.message_id,
        ],
        start_to_close_timeout=timedelta(seconds=15),
        retry_policy=_short_retry,
      )

    finally:
      await self._safe_unreact(req, EYES)

  async def _gather_context(self, req: ChatRequest) -> tuple[str, list, list]:
    lore = await workflow.execute_activity(
      manager.fetch_prompt,
      req.server_id,
      start_to_close_timeout=timedelta(seconds=10),
      retry_policy=_short_retry,
    )
    history = await workflow.execute_activity(
      manager.get_chat_history,
      req.server_id,
      start_to_close_timeout=timedelta(seconds=10),
      retry_policy=_short_retry,
    )
    memories = await workflow.execute_activity(
      manager.get_memories,
      args=[req.server_id, req.author_id],
      start_to_close_timeout=timedelta(seconds=10),
      retry_policy=_short_retry,
    )
    return lore, history, memories

  async def _safe_react(self, req: ChatRequest, emoji: str) -> None:
    try:
      await workflow.execute_activity(
        discord_rest.add_reaction,
        args=[req.channel_id, req.message_id, emoji],
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=RetryPolicy(maximum_attempts=2),
      )
    except Exception as e:
      workflow.logger.warning(f"Could not add reaction {emoji}: {e}")

  async def _safe_unreact(self, req: ChatRequest, emoji: str) -> None:
    try:
      await workflow.execute_activity(
        discord_rest.remove_reaction,
        args=[req.channel_id, req.message_id, emoji],
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=RetryPolicy(maximum_attempts=2),
      )
    except Exception as e:
      workflow.logger.warning(f"Could not remove reaction {emoji}: {e}")
