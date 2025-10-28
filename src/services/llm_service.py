import io
import time
import base64
import json
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
  discord_agent_tool,
  discord_agent,
)
from utils.llm_utils import has_vision_content, to_base64_data_uri
from utils.singleton import Singleton


class LLMService(metaclass=Singleton):
  def __init__(self):
    self.client = OpenAI(
      base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY
    )
    self.model = OPENROUTER_MODEL

    # Map of tool names to their functions
    self.tool_functions = {
      "get_hackernews_stories": get_top_hn_stories,
      "search_web": search_web,
      "run_code": run_code,
      "generate_image": self._generate_image_as_tool,
      "discord_agent": lambda query: discord_agent(query, self),
    }

    # Tool definitions for OpenAI API
    self.tool_definitions = [
      hackernews_tool,
      tavily_search_tool,
      sandbox_tool,
      generate_image_tool,
      discord_agent_tool,
    ]

  def create_or_edit_image(
    self,
    prompt: str,
    input_image: Optional[Union[io.BytesIO, bytes]] = None,
    aspect_ratio: str = "1:1",
  ) -> Union[bytes, str]:
    """
    Generate or edit an image.
    Returns raw image bytes (base64 string) on success or error message.
    """
    image_model = "google/gemini-2.5-flash-image"
    logger.info(f"Image task with model: {image_model}")

    try:
      # Prepare messages
      if input_image:
        logger.info("Mode: Image Editing")
        base64_image_data = to_base64_data_uri(input_image)
        content = [
          {"type": "image_url", "image_url": {"url": base64_image_data}},
          {"type": "text", "text": prompt},
        ]
        chat_messages = [{"role": "user", "content": content}]
      else:
        logger.info("Mode: Text-to-Image Generation")
        chat_messages = [{"role": "user", "content": prompt}]

      # API call
      response = self.client.chat.completions.create(
        model=image_model,
        messages=chat_messages,
        max_tokens=4096,
        extra_body={
          "modalities": ["image"],
          "image_config": {"aspect_ratio": aspect_ratio},
        },
      )

      message = response.choices[0].message

      # Extract image from response
      if hasattr(message, "model_extra") and message.model_extra:
        images = message.model_extra.get("images", [])
        if images and len(images) > 0:
          image_url = images[0].get("image_url", {}).get("url", "")
          if image_url:
            logger.info("Successfully received image data")
            # Extract base64 data
            if "base64," in image_url:
              _, base64_data = image_url.split(",", 1)
            else:
              base64_data = image_url
            return base64_data

      logger.warning("Model returned text instead of image")
      return "ERROR: No image returned"

    except Exception as e:
      return self._handle_api_error(e)

  def _generate_image_as_tool(self, prompt: str, aspect_ratio: str = "1:1") -> dict:
    """Wrapper for tool-calling mechanism."""
    logger.info(f"Tool call: generate_image with prompt: '{prompt}'")
    result = self.create_or_edit_image(prompt=prompt, aspect_ratio=aspect_ratio)

    # Handle result
    if isinstance(result, str):
      if (
        result.startswith("ERROR") or result.startswith("⏳") or result.startswith("😵")
      ):
        return {"status": "error", "message": result}

      # It's base64 data
      b64 = result
      if b64.startswith("data:") and "," in b64:
        _, b64 = b64.split(",", 1)

      return {
        "status": "success",
        "message": f"Image generated for '{prompt}'",
        "image_data": b64,
        "format": "png",
      }

    return {"status": "error", "message": "Unexpected result type"}

  def chat_completions(
    self,
    prompt: Optional[str] = None,
    image: Optional[Union[io.BytesIO, bytes, str]] = None,
    messages: Optional[Union[str, List[Dict[str, str]]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 512,
    enable_tools: bool = False,  # Changed to False by default
    tools: Optional[List[str]] = None,
  ) -> tuple:
    """
    Main chat completion with tool calling.
    Returns: (response_text, usage, generated_images)
    """
    mock_usage = type("Usage", (), {"prompt_tokens": 0, "total_tokens": 0})()

    try:
      # Prepare messages
      if image:
        image_url = image if isinstance(image, str) else to_base64_data_uri(image)
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

      # Check if vision mode (disable tools for vision)
      vision_mode = has_vision_content(chat_messages)

      # Prepare API parameters
      api_params = {
        "model": self.model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
      }

      # Add tools if enabled and not vision mode
      if enable_tools and not vision_mode:
        api_params["tools"] = self.tool_definitions
        # Only use tools when explicitly requested
        api_params["tool_choice"] = "auto"

      # Initial API call
      response = self.client.chat.completions.create(**api_params)
      message = response.choices[0].message

      # Check for tool calls
      if hasattr(message, "tool_calls") and message.tool_calls:
        return self._handle_tool_calls(
          message, chat_messages, max_tokens, temperature, response.usage
        )

      # No tool calls - return response directly
      return message.content.strip(), response.usage, []

    except Exception as e:
      logger.error(f"Error in chat_completions: {e}")
      return self._handle_api_error(e), mock_usage, []

  def describe_image(
    self,
    image: Union[io.BytesIO, bytes, str],
    prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
  ) -> str:
    """
    Convenience method to describe an image.

    Args:
        image: Image as BytesIO, bytes, or base64 string
        prompt: Optional custom prompt (uses default if not provided)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
        Image description/caption as string
    """
    default_prompt = (
      "Please provide a detailed description of this image. "
      "Include objects, people, colors, setting, and any notable details."
    )

    caption, _, _ = self.chat_completions(
      prompt=prompt or default_prompt,
      image=image,
      temperature=temperature,
      max_tokens=max_tokens,
      enable_tools=False,  # Disable tools for image description
    )

    return caption.strip()

  def _handle_tool_calls(
    self, message, chat_messages: List[Dict], max_tokens: int, temperature: float, usage
  ) -> tuple:
    """Handle tool calls in standard OpenAI format."""
    generated_images = []
    tool_results = []

    # Execute each tool call
    for tool_call in message.tool_calls:
      function_name = tool_call.function.name
      logger.info(f"Executing tool: {function_name}")

      try:
        # Parse arguments
        arguments = json.loads(tool_call.function.arguments)

        # Execute function
        if function_name in self.tool_functions:
          result = self.tool_functions[function_name](**arguments)
        else:
          result = {"error": f"Unknown function: {function_name}"}

        # Convert result to JSON string
        result_str = json.dumps(result)

        # Check for image generation
        if (
          function_name == "generate_image"
          and result.get("status") == "success"
          and "image_data" in result
        ):
          generated_images.append(
            {
              "data": result["image_data"],
              "format": result.get("format", "png"),
            }
          )

        tool_results.append({"call": tool_call, "result": result_str})

      except Exception as e:
        logger.error(f"Error executing {function_name}: {e}")
        error_result = json.dumps({"error": str(e)})
        tool_results.append({"call": tool_call, "result": error_result})

    # If image was generated, return immediately
    if generated_images:
      return "Here's your generated image! 🎨", usage, generated_images

    # Add assistant message with tool calls
    chat_messages.append(
      {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
          {
            "id": tr["call"].id,
            "type": "function",
            "function": {
              "name": tr["call"].function.name,
              "arguments": tr["call"].function.arguments,
            },
          }
          for tr in tool_results
        ],
      }
    )

    # Add tool results
    for tr in tool_results:
      chat_messages.append(
        {"role": "tool", "tool_call_id": tr["call"].id, "content": tr["result"]}
      )

    # Get final response
    final_response = self.client.chat.completions.create(
      model=self.model,
      messages=chat_messages,
      max_tokens=max_tokens,
      temperature=temperature,
    )

    return final_response.choices[0].message.content.strip(), final_response.usage, []

  def _handle_api_error(self, error: Exception) -> str:
    """Handle API errors with user-friendly messages."""
    if (
      hasattr(error, "response") and getattr(error.response, "status_code", None) == 429
    ):
      headers = getattr(error.response, "headers", {})
      reset_ts = int(headers.get("X-RateLimit-Reset", "0"))
      wait_sec = max(0, reset_ts - int(time.time()))
      formatted = f"{wait_sec // 60}m {wait_sec % 60}s"
      logger.warning(f"Rate limit hit. Wait {formatted}.")
      return f"⏳ Rate limit hit. Try again in {formatted}."

    logger.error(f"Unexpected error: {error}")
    return "😵 Something went wrong while generating a response."
