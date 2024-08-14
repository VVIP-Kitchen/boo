import requests
from utils.config import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_WORKERS_AI_API_KEY, MODEL_NAME


def call_model(messages):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct-awq"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}
    json = {"messages": messages}
    bot_response = ""

    try:
        response = requests.post(url, headers=headers, json=json)
        result = response.json()
        bot_response = str(result["result"]["response"])
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        bot_response = (
            "Sorry, I'm having trouble thinking right now. Can you try again later?"
        )
    except KeyError:
        print("Unexpected API response format")
        bot_response = "I'm a bit confused. Can you rephrase that?"

    return bot_response
