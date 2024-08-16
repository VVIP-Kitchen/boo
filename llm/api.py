import requests
from utils.config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_WORKERS_AI_API_KEY,
    MODEL_NAME,
)


def call_model(messages):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL_NAME}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}
    json = {"messages": messages}
    bot_response = ""

    try:
        response = requests.post(url, headers=headers, json=json)
        result = response.json()
        bot_response = str(result["result"]["response"])
        bot_response = (
            bot_response
            if len(bot_response) != 0
            else "Cloudflare Workers AI returned empty string. Change model maybe!"
        )
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        bot_response = (
            "Sorry, I'm having trouble thinking right now. Can you try again later?"
        )
    except KeyError:
        print("Unexpected API response format")
        bot_response = "I'm a bit confused. Can you rephrase that?"

    return bot_response


def fetch_models():
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/models/search"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}
    models = []

    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        for obj in result["result"]:
            if "meta" in obj["name"]:
                models.append(obj["name"])
    except Exception as e:
        print(str(e))

    return models
