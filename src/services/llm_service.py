import io
import time
import json
from openai import OpenAI
from typing import List, Dict, Union, Optional

from utils.logger import logger
from utils.config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from services.tool_calling_service import (
  hackernews_tool,
  get_top_hn_stories,
  exa_search_tool,
  search_web,
  sandbox_tool,
  run_code,
  generate_image_tool,
  read_pdf_tool,
  read_pdf,
  read_csv_tool,
  read_csv,
  github_repo_info_tool,
  get_github_repo_info,
  github_search_tool,
  search_github,
  github_trending_tool,
  get_trending_repos,
)
from utils.llm_utils import to_base64_data_uri
from utils.singleton import Singleton

MAX_TOOL_ROUNDS = 5


class LLMService(metaclass=Singleton):
  def __init__(self):
    self.client = OpenAI(
      base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY
    )
    self.model = OPENROUTER_MODEL

    self.tool_functions = {
      "get_hackernews_stories": get_top_hn_stories,
      "search_web": search_web,
      "run_code": run_code,
      "generate_image": self._generate_image_as_tool,
      "read_pdf": read_pdf,
      "read_csv": read_csv,
      "get_github_repo_info": get_github_repo_info,
      "search_github": search_github,
      "get_trending_repos": get_trending_repos,
    }

    self.tool_definitions = [
      hackernews_tool,
      exa_search_tool,
      sandbox_tool,
      generate_image_tool,
      read_pdf_tool,
      read_csv_tool,
      github_repo_info_tool,
      github_search_tool,
      github_trending_tool,
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
    image_model = "google/gemini-3.1-flash-image-preview"
    logger.info(f"Image task with model: {image_model}")

    try:
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

      if hasattr(message, "model_extra") and message.model_extra:
        images = message.model_extra.get("images", [])
        if images and len(images) > 0:
          image_url = images[0].get("image_url", {}).get("url", "")
          if image_url:
            logger.info("Successfully received image data")
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

    if isinstance(result, str):
      if (
        result.startswith("ERROR") or result.startswith("⏳") or result.startswith("😵")
      ):
        return {"status": "error", "message": result}

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
    max_tokens: int = 4096,
    enable_tools: bool = False,
  ) -> tuple:
    """
    Main chat completion with multi-round tool calling.
    The model can chain multiple tool calls across up to MAX_TOOL_ROUNDS rounds.
    Returns: (response_text, usage, generated_images)
    """
    mock_usage = type("Usage", (), {"prompt_tokens": 0, "total_tokens": 0})()

    try:
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

      api_params = {
        "model": self.model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
      }

      if enable_tools:
        api_params["tools"] = self.tool_definitions
        api_params["tool_choice"] = "auto"

      all_generated_images = []
      latest_usage = mock_usage

      for _round in range(MAX_TOOL_ROUNDS):
        response = self.client.chat.completions.create(**api_params)
        message = response.choices[0].message
        latest_usage = response.usage

        if not (hasattr(message, "tool_calls") and message.tool_calls):
          text = (message.content or "").strip()
          return text, latest_usage, all_generated_images

        tool_results, generated_images = self._execute_tool_calls(message)
        all_generated_images.extend(generated_images)

        if generated_images:
          return "Here's your generated image! 🎨", latest_usage, all_generated_images

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

        for tr in tool_results:
          chat_messages.append(
            {"role": "tool", "tool_call_id": tr["call"].id, "content": tr["result"]}
          )

        api_params["messages"] = chat_messages

      # Max rounds exhausted -- get a final text response without tools
      api_params.pop("tools", None)
      api_params.pop("tool_choice", None)
      final_response = self.client.chat.completions.create(**api_params)
      text = (final_response.choices[0].message.content or "").strip()
      return text, final_response.usage, all_generated_images

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
      enable_tools=False,
    )

    return caption.strip()

  def _execute_tool_calls(self, message) -> tuple:
    """
    Execute all tool calls from the model's response.
    Returns: (tool_results, generated_images)
    """
    generated_images = []
    tool_results = []

    for tool_call in message.tool_calls:
      function_name = tool_call.function.name
      logger.info(f"Executing tool: {function_name}")

      try:
        arguments = json.loads(tool_call.function.arguments)

        if function_name in self.tool_functions:
          result = self.tool_functions[function_name](**arguments)
        else:
          result = {"error": f"Unknown function: {function_name}"}

        result_str = json.dumps(result)

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

    return tool_results, generated_images

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
