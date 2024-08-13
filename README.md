## **Boo** 🙈
A quirky chatter bot for Discord servers (currently serving VVIP Kitchen)

## **Steps to run**
1. Clone this repo
2. Register for [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai)
3. Store the API keys and account ID provided by Cloudflare in your environment variables (check [bot.py](./bot.py) code for reference)
4. Login to [Discord's developer portal](https://discord.dev) and create a new application with bot enabled on it
5. Create a `DISCORD_TOKEN` and store it in your environment variables of the same name (check [bot.py](./bot.py) code for reference)
6. Install dependencies and run
```sh
git clone git@github.com:kashifulhaque/boo.git;
cd boo;
python3 -m venv .venv; source .venv/bin/activate; # OPTIONAL, but recommended
python -m pip install -r requirements.txt;
python bot.py;
```
