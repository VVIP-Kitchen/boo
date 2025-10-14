import io
import json
import time
import base64
import os
import uuid  # For generating unique filenames
from openai import OpenAI
from typing import List, Dict, Union, Optional
from utils.logger import logger
from utils.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

from services.tool_calling_service import (
  hackernews_tool,
  get_top_hn_stories,
  tavily_search_tool,
  search_web,
  sandbox_tool,
  run_code,
  generate_image_tool,
)


class LLMService:
  def __init__(self):
    self.client = OpenAI(
      base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY
    )
    self.model = OPENROUTER_MODEL
    self.available_tools = {
      "get_hackernews_stories": {
        "tool_definition": hackernews_tool,
        "function": get_top_hn_stories,
      },
      "search_web": {"tool_definition": tavily_search_tool, "function": search_web},
      "run_code": {"tool_definition": sandbox_tool, "function": run_code},
      "generate_image": {
        "tool_definition": generate_image_tool,
        "function": self._generate_image_as_tool,
      },
    }

  def create_or_edit_image(
    self,
    prompt: str,
    input_image: Optional[Union[io.BytesIO, bytes]] = None,
    aspect_ratio: str = "1:1",
  ) -> Union[bytes, str]:
    """
    Directly generates or edits an image. This can be called programmatically.
    Returns raw image bytes on success or an error string on failure.
    """
    image_model = "google/gemini-2.5-flash-image"
    logger.info(f"Initiating image task with model: {image_model}")
    try:
      if input_image:
        logger.info("Mode: Image Editing")
        base64_image_data = self._to_base64_data_uri(input_image)
        content = [
          {"type": "image_url", "image_url": {"url": base64_image_data}},
          {"type": "text", "text": prompt},
        ]
        chat_messages = [{"role": "user", "content": content}]
      else:
        logger.info("Mode: Text-to-Image Generation")
        chat_messages = [{"role": "user", "content": prompt}]

      api_params = {
        "model": image_model,
        "messages": chat_messages,
        "max_tokens": 4096,
        "extra_body": {
          "modalities": ["image"],
          "image_config": {
            "aspect_ratio": aspect_ratio
          }
        }
      }

      response = self.client.chat.completions.create(**api_params)
      message = response.choices[0].message

      # Try to get images from the model_extra field (where OpenAI SDK stores unknown fields)
      if hasattr(message, 'model_extra') and message.model_extra:
        images = message.model_extra.get('images', [])
        if images and len(images) > 0:
          image_url = images[0].get('image_url', {}).get('url', '')
          if image_url:
            logger.info("Successfully received image data from API")
            # Extract base64 data
            if "base64," in image_url:
              _, base64_data = image_url.split(",", 1)
            else:
              base64_data = image_url
            return base64_data

      logger.warning(f"Model returned text instead of image")
      return "ERROR: No image returned"
    except Exception as e:
      if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
        headers = getattr(e.response, "headers", {})
        reset_ts = int(headers.get("X-RateLimit-Reset", "0"))
        wait_sec = max(0, reset_ts - int(time.time()))
        formatted = f"{wait_sec // 60}m {wait_sec % 60}s"
        logger.warning(f"Rate limit hit. Waiting for {formatted}.")
        return f"⏳ Rate limit hit. Try again in {formatted}."

      logger.error(f"Unexpected error in create_or_edit_image: {e}")
      return "😵 Something went wrong while generating the image."

  def _generate_image_as_tool(self, prompt: str, aspect_ratio: str = "1:1") -> dict:
    """
    Wrapper for the tool-calling mechanism. It saves the generated image
    and returns a JSON-serializable dictionary as the result.
    """
    logger.info(f"Tool call received: generate_image with prompt: '{prompt}'")

    # Call the core image generation logic
    result = self.create_or_edit_image(prompt=prompt, aspect_ratio=aspect_ratio)

    # If core returned raw bytes, base64-encode them so the tool result is JSON-serializable
    if isinstance(result, (bytes, bytearray)):
      image_b64 = base64.b64encode(result).decode("utf-8")
      return {
        "status": "success",
        "message": f"Image successfully generated for prompt '{prompt}'",
        "image_data": image_b64,
        "format": "png",
      }

    # If core returned a string, assume it's already base64 (or data URI). Normalize it.
    if isinstance(result, str):
      b64 = result
      # If it's a data URI like "data:image/png;base64,AAAA...", strip the prefix.
      if b64.startswith("data:") and "," in b64:
        _, b64 = b64.split(",", 1)

      # sanity check: quick length check to avoid returning error messages as "image"
      if len(b64) < 50:
        # probably an error message like "ERROR: No image returned"
        return {"status": "error", "message": result}

      return {
        "status": "success",
        "message": f"Image successfully generated for prompt '{prompt}'",
        "image_data": b64,
        "format": "png",
      }

    # fallback: unexpected type -> treat as error
    return {"status": "error", "message": str(result)}

  def _to_base64_data_uri(self, image: Union[io.BytesIO, bytes]) -> str:
    image_bytes = image.getvalue() if isinstance(image, io.BytesIO) else image
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_str}"

  def _has_vision_content(self, messages):
    try:
      for m in messages or []:
        c = m.get("content")
        if isinstance(c, list):
          for item in c:
            if isinstance(item, dict) and item.get("type") == "image_url":
              return True
    except Exception:
      pass
    return False

  def _execute_tool_call(self, tool_call) -> str:
    function_name = tool_call.function.name

    if function_name not in self.available_tools:
      return json.dumps({"error": f"Unknown function: {function_name}"})

    try:
      arguments = json.loads(tool_call.function.arguments)
      function = self.available_tools[function_name]["function"]
      result = function(**arguments)
      return json.dumps(result)
    except Exception as e:
      return json.dumps({"error": f"Error executing {function_name}: {str(e)}"})

  def chat_completions(
    self,
    prompt: Optional[str] = None,
    image: Optional[Union[io.BytesIO, bytes, str]] = None,
    messages: Optional[Union[str, List[Dict[str, str]]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 512,
    enable_tools: bool = True,
    tools: Optional[List[str]] = None,
  ) -> tuple:
    try:
      mock_usage = type("Usage", (), {"prompt_tokens": 0, "total_tokens": 0})()
      generated_images = []

      if image:
        image_url = image if isinstance(image, str) else self._to_base64_data_uri(image)
        content = [
          {"type": "text", "text": prompt or "Describe this image."},
          {"type": "image_url", "image_url": {"url": image_url}},
        ]
        chat_messages = [{"role": "user", "content": content}]
      elif messages:
        chat_messages = (
          [{"role": "user", "content": messages}]
          if isinstance(messages, str)
          else messages
        )
      elif prompt:
        chat_messages = [{"role": "user", "content": prompt}]
      else:
        return "⚠️ No input provided.", mock_usage, []

      api_params = {
        "model": self.model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
      }

      vision_mode = self._has_vision_content(chat_messages)
      if enable_tools and not vision_mode:
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

      if not vision_mode and hasattr(message, "tool_calls") and message.tool_calls:
        for tool_call in message.tool_calls:
          tool_result = self._execute_tool_call(tool_call)
          if tool_result is None:
            tool_result = json.dumps({"error": "Tool returned None"})

          try:
            tool_result_dict = json.loads(tool_result)
          except json.JSONDecodeError:
            tool_result_dict = {"error": "Invalid JSON response"}

          # Check if this is an image generation result
          if (
            tool_call.function.name == "generate_image"
            and tool_result_dict.get("status") == "success"
            and "image_data" in tool_result_dict
          ):
            generated_images.append(
              {
                "data": tool_result_dict["image_data"],
                "format": tool_result_dict.get("format", "png"),
              }
            )

            # Return immediately for image generation - no second API call needed
            simple_message = "Here's your generated image! 🎨"
            return simple_message, response.usage, generated_images

        # For non-image tools, add to context for final response
        chat_messages.append(
          {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
              {
                "id": tool_call.id,
                "type": "function",
                "function": {
                  "name": tool_call.function.name,
                  "arguments": tool_call.function.arguments,
                },
              }
            ],
          }
        )
        chat_messages.append(
          {"role": "tool", "tool_call_id": tool_call.id, "content": tool_result}
        )
        final_response = self.client.chat.completions.create(
          model=self.model,
          messages=chat_messages,
          max_tokens=max_tokens,
          temperature=temperature,
        )

        return (
          final_response.choices[0].message.content.strip(),
          final_response.usage,
          [],
        )

      else:
        return message.content.strip(), response.usage, []

    except Exception as e:
      if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
        headers = getattr(e.response, "headers", {})
        reset_ts = int(headers.get("X-RateLimit-Reset", "0"))
        current_ts = int(time.time())
        wait_sec = max(0, reset_ts - current_ts)

        mins = wait_sec // 60
        secs = wait_sec % 60
        formatted = f"{mins}m {secs}s" if mins else f"{secs}s"

        return (
          f"⏳ You've hit the rate limit for this model. Try again in {formatted}.",
          mock_usage,
          []
        )

      logger.error(f"Unexpected error in chat_completions: {e}")
      return "😵 Something went wrong while generating a response.", mock_usage, []
