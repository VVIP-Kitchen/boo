import requests
from config import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_WORKERS_AI_API_KEY


async def get_ai_response(messages):
    try:
        response = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct-awq",
            headers={"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"},
            json={"messages": messages},
        )
        response.raise_for_status()
        result = response.json()
        return str(result["result"]["response"])
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return "Sorry, I'm having trouble thinking right now. Can you try again later?"
    except KeyError:
        print("Unexpected API response format")
        return "I'm a bit confused. Can you rephrase that?"
