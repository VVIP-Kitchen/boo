import requests
from datetime import datetime, timedelta

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
          "default": 20
        }
      }
    }
  }
}

def fetch_top_stories():
  try:
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    response.raise_for_status()

    return response.json()
  except requests.RequestException as e:
    return {
      "error": f"Failed to fetch top stories: {str(e)}"
    }

def fetch_story(story_id):
  try:
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    response = requests.get(url)
    response.raise_for_status()

    return response.json()
  except requests.RequestException as e:
    return {
      "error": f"Failed to fetch story {story_id}: {str(e)}"
    }

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
        stories.append({
          "id": story.get("id"),
          "title": story.get("title", ""),
          "url": story.get("url", ""),
          "score": story.get("score", 0),
          "by": story.get("by", ""),
          "time": story.get("time", 0),
          "descendants": story.get("descendants", 0)
        })
  
  stories.sort(key=lambda x: x["score"], reverse=True)
  return stories[:limit]
