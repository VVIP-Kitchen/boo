import io
import base64
import requests
import pandas as pd
from PyPDF2 import PdfReader
from tavily import TavilyClient
from datetime import datetime, timedelta
from utils.config import TAVILY_API_KEY, GITHUB_TOKEN

### Hackernews
hackernews_tool = {
  "type": "function",
  "function": {
    "name": "get_hackernews_stories",
    "description": "Fetch top stories from Hacker News. Use ONLY when the user explicitly asks for Hacker News stories or HN content.",
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
    "description": "Search the web for real-time information. Use ONLY when the user explicitly requests a web search or asks for current/live information that you don't have in your training data.",
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


### PDF Reader
read_pdf_tool = {
  "type": "function",
  "function": {
    "name": "read_pdf",
    "description": "Read the text content of a PDF file from a URL.",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "The URL of the PDF file to read.",
        },
      },
      "required": ["url"],
    },
  },
}


def read_pdf(url: str):
  try:
    response = requests.get(url)
    response.raise_for_status()
    pdf_file = io.BytesIO(response.content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
      text += page.extract_text()
    return {"text": text}
  except Exception as e:
    return {"error": f"Failed to read PDF: {str(e)}"}


### CSV Reader
read_csv_tool = {
  "type": "function",
  "function": {
    "name": "read_csv",
    "description": "Read the text content of a CSV file from a URL.",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "The URL of the CSV file to read.",
        },
      },
      "required": ["url"],
    },
  },
}


def read_csv(url: str):
  try:
    df = pd.read_csv(url)
    return {"data": df.head().to_string()}
  except Exception as e:
    return {"error": f"Failed to read CSV: {str(e)}"}


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
    "description": "Execute Python code in a secure sandbox. Use ONLY when the user explicitly asks to run or execute code.",
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
    "description": "Generate an image from a text description. Use ONLY when the user explicitly asks to create, draw, generate, or make an image/picture.",
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

### GitHub Integration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_HEADERS = {
  "Accept": "application/vnd.github.v3+json",
  "User-Agent": "Discord-Bot-LLM-Service",
}
if GITHUB_TOKEN:
  GITHUB_HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# Tool 1: Get Repository Info
github_repo_info_tool = {
  "type": "function",
  "function": {
    "name": "get_github_repo_info",
    "description": "Get detailed information about a GitHub repository from its URL or owner/repo format. Returns metadata including owner, stars, forks, languages, latest commit, and readme excerpt.",
    "parameters": {
      "type": "object",
      "properties": {
        "repo_identifier": {
          "type": "string",
          "description": "GitHub repository in format 'owner/repo' or full GitHub URL",
        },
      },
      "required": ["repo_identifier"],
    },
  },
}

def get_github_repo_info(repo_identifier: str):
  """
  Fetch detailed information about a GitHub repository.
  
  Args:
    repo_identifier: Either 'owner/repo' or full GitHub URL
  
  Returns:
    Dictionary with repo metadata, languages, latest commit, and readme excerpt
  """
  try:
    # Parse the identifier
    if "github.com" in repo_identifier:
      # Extract owner/repo from URL
      parts = repo_identifier.rstrip("/").split("/")
      owner, repo = parts[-2], parts[-1]
    else:
      # Assume format is owner/repo
      owner, repo = repo_identifier.split("/")
    
    # Fetch repository data
    repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    repo_response = requests.get(repo_url, headers=GITHUB_HEADERS)
    repo_response.raise_for_status()
    repo_data = repo_response.json()
    
    # Fetch languages
    languages_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
    languages_response = requests.get(languages_url, headers=GITHUB_HEADERS)
    languages = languages_response.json() if languages_response.ok else {}
    
    # Fetch latest commit
    commits_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    commits_response = requests.get(commits_url, headers=GITHUB_HEADERS, params={"per_page": 1})
    latest_commit = None
    if commits_response.ok:
      commits = commits_response.json()
      if commits:
        latest_commit = {
          "sha": commits[0]["sha"][:7],
          "message": commits[0]["commit"]["message"].split("\n")[0],
          "author": commits[0]["commit"]["author"]["name"],
          "date": commits[0]["commit"]["author"]["date"],
        }
    
    # Fetch branches count
    branches_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches"
    branches_response = requests.get(branches_url, headers=GITHUB_HEADERS)
    branches_count = len(branches_response.json()) if branches_response.ok else 0
    
    # Fetch README excerpt
    readme_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    readme_response = requests.get(readme_url, headers=GITHUB_HEADERS)
    readme_excerpt = None
    if readme_response.ok:
      readme_data = readme_response.json()
      # GitHub returns base64 encoded content
      readme_content = base64.b64decode(readme_data.get("content", "")).decode("utf-8")
      # Get first 500 characters
      readme_excerpt = readme_content[:500] + ("..." if len(readme_content) > 500 else "")
    
    # Compile response
    return {
      "name": repo_data.get("name"),
      "full_name": repo_data.get("full_name"),
      "owner": repo_data.get("owner", {}).get("login"),
      "description": repo_data.get("description"),
      "url": repo_data.get("html_url"),
      "stars": repo_data.get("stargazers_count"),
      "forks": repo_data.get("forks_count"),
      "watchers": repo_data.get("watchers_count"),
      "open_issues": repo_data.get("open_issues_count"),
      "default_branch": repo_data.get("default_branch"),
      "branches_count": branches_count,
      "language": repo_data.get("language"),
      "languages": languages,
      "created_at": repo_data.get("created_at"),
      "updated_at": repo_data.get("updated_at"),
      "pushed_at": repo_data.get("pushed_at"),
      "size_kb": repo_data.get("size"),
      "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
      "topics": repo_data.get("topics", []),
      "latest_commit": latest_commit,
      "readme_excerpt": readme_excerpt,
    }
    
  except requests.HTTPError as e:
    if e.response.status_code == 404:
      return {"error": f"Repository not found: {repo_identifier}"}
    elif e.response.status_code == 403:
      return {"error": "GitHub API rate limit exceeded. Try again later or add a GitHub token."}
    else:
      return {"error": f"GitHub API error: {e.response.status_code}"}
  except Exception as e:
    return {"error": f"Failed to fetch repository info: {str(e)}"}


# Tool 2: Search GitHub
github_search_tool = {
  "type": "function",
  "function": {
    "name": "search_github",
    "description": "Search for GitHub repositories or users. Returns top results with relevant information.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query (e.g., 'machine learning', 'tensorflow', 'user:google')",
        },
        "search_type": {
          "type": "string",
          "description": "Type of search to perform",
          "enum": ["repositories", "users"],
          "default": "repositories",
        },
        "max_results": {
          "type": "integer",
          "description": "Maximum number of results to return (default: 5, max: 10)",
          "default": 5,
        },
        "sort": {
          "type": "string",
          "description": "Sort field for repositories (stars, forks, updated) or users (followers, repositories, joined)",
          "default": "stars",
        },
      },
      "required": ["query"],
    },
  },
}


def search_github(query: str, search_type: str = "repositories", max_results: int = 5, sort: str = "stars"):
  """
  Search GitHub for repositories or users.
  
  Args:
    query: Search query string
    search_type: Either 'repositories' or 'users'
    max_results: Number of results to return (1-10)
    sort: Sort field
  
  Returns:
    Dictionary with search results
  """
  try:
    max_results = min(max(1, max_results), 10)
    
    if search_type == "repositories":
      search_url = f"{GITHUB_API_BASE}/search/repositories"
      params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": max_results,
      }
    else:  # users
      search_url = f"{GITHUB_API_BASE}/search/users"
      params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": max_results,
      }
    
    response = requests.get(search_url, headers=GITHUB_HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    
    results = []
    if search_type == "repositories":
      for repo in data.get("items", []):
        results.append({
          "name": repo.get("full_name"),
          "description": repo.get("description"),
          "url": repo.get("html_url"),
          "stars": repo.get("stargazers_count"),
          "forks": repo.get("forks_count"),
          "language": repo.get("language"),
          "updated_at": repo.get("updated_at"),
          "topics": repo.get("topics", [])[:5],  # Limit topics
        })
    else:  # users
      for user in data.get("items", []):
        results.append({
          "username": user.get("login"),
          "name": user.get("name"),
          "url": user.get("html_url"),
          "avatar_url": user.get("avatar_url"),
          "bio": user.get("bio"),
          "type": user.get("type"),
          "followers": user.get("followers"),
          "public_repos": user.get("public_repos"),
        })
    
    return {
      "query": query,
      "search_type": search_type,
      "total_count": data.get("total_count", 0),
      "results": results,
      "results_returned": len(results),
    }
    
  except requests.HTTPError as e:
    if e.response.status_code == 403:
      return {"error": "GitHub API rate limit exceeded. Try again later or add a GitHub token."}
    else:
      return {"error": f"GitHub API error: {e.response.status_code}"}
  except Exception as e:
    return {"error": f"Failed to search GitHub: {str(e)}"}


# Tool 3: Get Trending Repositories
github_trending_tool = {
  "type": "function",
  "function": {
    "name": "get_trending_repos",
    "description": "Discover trending repositories on GitHub. Finds popular and recently active repositories.",
    "parameters": {
      "type": "object",
      "properties": {
        "language": {
          "type": "string",
          "description": "Programming language filter (e.g., 'python', 'javascript', 'rust'). Leave empty for all languages.",
          "default": "",
        },
        "since": {
          "type": "string",
          "description": "Time period for trending repos",
          "enum": ["daily", "weekly", "monthly"],
          "default": "weekly",
        },
        "max_results": {
          "type": "integer",
          "description": "Maximum number of results to return (default: 10, max: 20)",
          "default": 10,
        },
      },
    },
  },
}


def get_trending_repos(language: str = "", since: str = "weekly", max_results: int = 10):
  """
  Get trending repositories from GitHub.
  
  Since GitHub doesn't have an official trending API, we use search with
  recent activity and high stars as a proxy.
  
  Args:
    language: Programming language filter
    since: Time period (daily, weekly, monthly)
    max_results: Number of results to return
  
  Returns:
    Dictionary with trending repositories
  """
  try:
    max_results = min(max(1, max_results), 20)
    
    # Calculate date range
    date_delta = {"daily": 1, "weekly": 7, "monthly": 30}
    date_filter = (datetime.now() - timedelta(days=date_delta[since])).strftime("%Y-%m-%d")
    
    # Build query
    query_parts = [f"created:>{date_filter}", "stars:>10"]
    if language:
      query_parts.append(f"language:{language}")
    
    query = " ".join(query_parts)
    
    # Search for trending repos
    search_url = f"{GITHUB_API_BASE}/search/repositories"
    params = {
      "q": query,
      "sort": "stars",
      "order": "desc",
      "per_page": max_results,
    }
    
    response = requests.get(search_url, headers=GITHUB_HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    
    results = []
    for repo in data.get("items", []):
      results.append({
        "name": repo.get("full_name"),
        "description": repo.get("description"),
        "url": repo.get("html_url"),
        "stars": repo.get("stargazers_count"),
        "forks": repo.get("forks_count"),
        "language": repo.get("language"),
        "created_at": repo.get("created_at"),
        "topics": repo.get("topics", [])[:5],
      })
    
    return {
      "language": language if language else "all",
      "time_period": since,
      "total_found": data.get("total_count", 0),
      "results": results,
      "results_returned": len(results),
    }
    
  except requests.HTTPError as e:
    if e.response.status_code == 403:
      return {"error": "GitHub API rate limit exceeded. Try again later or add a GitHub token."}
    else:
      return {"error": f"GitHub API error: {e.response.status_code}"}
  except Exception as e:
    return {"error": f"Failed to fetch trending repos: {str(e)}"}