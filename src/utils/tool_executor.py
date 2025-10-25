import json
from typing import Dict, List
from utils.logger import logger


class ToolExecutor:
  """Handles tool call execution and result processing."""

  def __init__(self, available_tools: Dict):
    self.available_tools = available_tools

  def execute_tool_call(self, call_dict: dict) -> str:
    """
    Execute a tool call from various format shapes.

    Args:
      call_dict: Tool call in format:
        - {"name": "...", "parameters": {...}}
        - {"function": {"name": "...", "arguments": "..."}}

    Returns:
      JSON string result
    """
    name = None
    try:
      # Parse different tool call formats
      if "name" in call_dict and "parameters" in call_dict:
        name = call_dict["name"]
        args = call_dict["parameters"]
      elif "function" in call_dict and isinstance(call_dict["function"], dict):
        fn = call_dict["function"]
        name = fn.get("name") or fn.get("function_name")
        args_raw = fn.get("arguments") or fn.get("parameters") or "{}"
        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
      else:
        name = call_dict.get("name")
        args = call_dict.get("parameters") or call_dict.get("arguments") or {}

      if not name or name not in self.available_tools:
        return json.dumps({"error": f"Unknown function name: {name}"})

      function = self.available_tools[name]["function"]
      result = function(**args)
      return json.dumps(result)

    except Exception as e:
      logger.error(f"Error executing {name}: {str(e)}")
      return json.dumps({"error": f"Error executing {name}: {str(e)}"})

  def is_image_generation_result(self, tool_name: str, result_dict: dict) -> bool:
    """Check if tool result is a successful image generation."""
    return (
      tool_name == "generate_image"
      and result_dict.get("status") == "success"
      and "image_data" in result_dict
    )

  def extract_image_data(self, result_dict: dict) -> dict:
    """Extract image data from tool result."""
    return {
      "data": result_dict["image_data"],
      "format": result_dict.get("format", "png"),
    }
