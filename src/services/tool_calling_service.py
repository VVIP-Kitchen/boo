import requests
from tavily import TavilyClient
from utils.config import TAVILY_API_KEY
from datetime import datetime, timedelta

### Hackernews
hackernews_tool = {
  "type": "function",
  "function": {
    "name": "get_hackernews_stories",
    "description": "Fetch top stories from Hacker News. Returns the top stories from the past week, sorted by score.",
    "parameters": {
      "type": "object",
      "properties": {
        "limit": {
          "type": "integer",
          "description": "Number of stories to return (default: 20, max: 50)",
          "default": 20,
        }
      },
    },
  },
}


def fetch_top_stories():
  try:
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    response.raise_for_status()

    return response.json()
  except requests.RequestException as e:
    return {"error": f"Failed to fetch top stories: {str(e)}"}


def fetch_story(story_id):
  try:
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    response = requests.get(url)
    response.raise_for_status()

    return response.json()
  except requests.RequestException as e:
    return {"error": f"Failed to fetch story {story_id}: {str(e)}"}


def get_top_hn_stories(limit=20):
  story_ids = fetch_top_stories()
  if isinstance(story_ids, dict) and "error" in story_ids:
    return story_ids

  stories = []
  last_week = int((datetime.now() - timedelta(days=7)).timestamp())

  for story_id in story_ids:
    if len(stories) >= limit:
      break

    story = fetch_story(story_id)
    if isinstance(story, dict) and "error" not in story:
      if story.get("time", 0) >= last_week and story.get("type") == "story":
        stories.append(
          {
            "id": story.get("id"),
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "score": story.get("score", 0),
            "by": story.get("by", ""),
            "time": story.get("time", 0),
            "descendants": story.get("descendants", 0),
          }
        )

  stories.sort(key=lambda x: x["score"], reverse=True)
  return stories[:limit]


### Tavily
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
tavily_search_tool = {
  "type": "function",
  "function": {
    "name": "search_web",
    "description": "Search the web using Tavily API for current information, news, and general queries.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query to find information about",
        },
        "max_results": {
          "type": "integer",
          "description": "Maximum number of results to return (default: 5, max: 10)",
          "default": 5,
        },
      },
      "required": ["query"],
    },
  },
}


def search_web(query, max_results=5):
  if not tavily_client:
    return {
      "error": "Tavily API key not configured. Please set TAVILY_API_KEY environment variable."
    }

  try:
    max_results = min(max(1, max_results), 10)
    response = tavily_client.search(query, max_results=max_results)

    formatted_results = []
    for result in response.get("results", []):
      formatted_results.append(
        {
          "title": result.get("title", ""),
          "url": result.get("url", ""),
          "content": result.get("content", ""),
          "score": result.get("score", 0),
        }
      )

    return {
      "query": query,
      "results": formatted_results,
      "total_results": len(formatted_results),
    }

  except Exception as e:
    return {"error": f"Failed to search web: {str(e)}"}


def get_tavily_usage():
  url = "https://api.tavily.com/usage"
  headers = {"Authorization": f"Bearer {TAVILY_API_KEY}"}

  response = requests.get(url, headers=headers)
  return response.json()


### Code running sandbox
sandbox_tool = {
  "type": "function",
  "function": {
    "name": "run_code",
    "description": "Execute Python code in a locked-down sandbox",
    "parameters": {
      "type": "object",
      "properties": {
        "code": {"type": "string", "description": "Python code to execute"},
        "timeout": {
          "type": "integer",
          "description": "Execution timeout (secs, max=10)",
          "default": 5,
        },
      },
      "required": ["code"],
    },
  },
}


def run_code(code: str, timeout: int = 5):
  try:
    resp = requests.post(
      "http://sandbox:8081/run", json={"code": code, "timeout": timeout}
    )
    return resp.json()
  except Exception as e:
    return {"error": f"Sandbox service unavailable: {str(e)}"}


### Image Generation Tool
generate_image_tool = {
  "type": "function",
  "function": {
    "name": "generate_image",
    "description": "Generates a new image from a textual description (prompt). This is used when a user explicitly asks to create, draw, or generate an image.",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "A detailed description of the image to be generated.",
        },
        "aspect_ratio": {
          "type": "string",
          "description": "The desired aspect ratio of the image.",
          "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"],
          "default": "1:1",
        },
      },
      "required": ["prompt"],
    },
  },
}
