import io
import json
import time
import base64
from openai import OpenAI
from typing import List, Dict, Union, Optional
from utils.logger import logger
from utils.config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from services.tool_calling_service import hackernews_tool, get_top_hn_stories


class LLMService:
  def __init__(self):
    self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    self.model = OPENROUTER_MODEL
    self.available_tools = {
      "get_hackernews_stories": {
        "tool_definition": hackernews_tool,
        "function": get_top_hn_stories
      }
    }

  def _to_base64_data_uri(self, image: Union[io.BytesIO, bytes]) -> str:
    image_bytes = image.getvalue() if isinstance(image, io.BytesIO) else image
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_str}"
  
  def _execute_tool_call(self, tool_call) -> str:
    function_name = tool_call.function.name

    if function_name not in self.available_tools:
      return json.dumps({
        "error": f"Unknown function: {function_name}"
      })
    
    try:
      arguments = json.loads(tool_call.function.arguments)
      function = self.available_tools[function_name]["function"]
      result = function(**arguments)
      return json.dumps(result)
    except Exception as e:
      return json.dumps({
        "error": f"Error executing {function_name}: {str(e)}"
      })

  def chat_completions(
    self,
    prompt: str = None,
    image: Union[io.BytesIO, bytes, str] = None,
    messages: Union[str, List[Dict[str, str]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 512,
    enable_tools: bool = True,
    tools: Optional[List[str]] = None
  ) -> str:
    try:
      mock_usage = type('Usage', (), {'prompt_tokens': 0, 'total_tokens': 0})()

      if image:
        image_url = image if isinstance(image, str) else self._to_base64_data_uri(image)
        content = [
          {"type": "text", "text": prompt or "Describe this image."},
          {"type": "image_url", "image_url": {"url": image_url}},
        ]
        chat_messages = [{"role": "user", "content": content}]
      elif messages:
        chat_messages = [{"role": "user", "content": messages}] if isinstance(messages, str) else messages
      elif prompt:
        chat_messages = [{"role": "user", "content": prompt}]
      else:
        return "⚠️ No input provided.", mock_usage

      api_params = {
        "model": self.model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {
          "enable_thinking": False
        }
      }

      if enable_tools:
        tool_definitions = []
        enabled_tools = tools or list(self.available_tools.keys())

        for tool_name in enabled_tools:
          if tool_name in self.available_tools:
            tool_definitions.append(self.available_tools[tool_name]["tool_definition"])
        
        if tool_definitions:
          api_params["tools"] = tool_definitions
          api_params["tool_choice"] = "auto"
        
      
      response = self.client.chat.completions.create(**api_params)
      message = response.choices[0].message

      if hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
          tool_result = self._execute_tool_call(tool_call)

          chat_messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [{
              "id": tool_call.id,
              "type": "function",
              "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
              }
            }]
          })

          chat_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
          })

          final_response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=temperature,
          )
          return final_response.choices[0].message.content.strip(), final_response.usage
      else:
        return message.content.strip(), response.usage
    except Exception as e:
      ### 429 + Retry time
      if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
        headers = getattr(e.response, "headers", {})
        reset_ts = int(headers.get("X-RateLimit-Reset", "0"))
        current_ts = int(time.time())
        wait_sec = max(0, reset_ts - current_ts)

        mins = wait_sec // 60
        secs = wait_sec % 60
        formatted = f"{mins}m {secs}s" if mins else f"{secs}s"

        return f"⏳ You've hit the rate limit for this model. Try again in {formatted}.", mock_usage
      
      ### Catch all
      logger.error(f"Unexpected error in chat_completions: {e}")
      return "😵 Something went wrong while generating a response.", mock_usage
