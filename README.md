## **Boo** 👻
A discord bot who talks to you! Boo supports natural language input like ChatGPT or Claude. It also understands images, give it a try! 

Powered by Meta's LLaMa 3.1

## **Tech stack**
- Python
- Discord.py
- Cloudflare
- Linode

## **Dev setup**
1. Clone this repo.
```sh
git clone https://github.com/VVIP-Kitchen/boo;
```
2. Register for [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai)
3. Store the API keys and account ID provided by Cloudflare in your environment variables (check [config.py](./utils/config.py) code for reference)
4. Login to [Discord's developer portal](https://discord.dev) and create a new application with bot enabled on it.
5. Create a `DISCORD_TOKEN` and store it in your environment variables of the same name (check [config.py](./utils/config.py) code for reference)
  6. Register for [Tenor API](https://tenor.com/gifapi/documentation) and [Tomorrow.IO](https://www.tomorrow.io/) and put their respective API keys in [config.py](./utils/config.py) too!
7. Install dependencies and run

```sh
git clone git@github.com:VVIP-Kitchen/boo.git;
cd boo;
python3 -m venv .venv; source .venv/bin/activate; # OPTIONAL, but recommended
python -m pip install -r requirements.txt;
python main.py;
```

## **Prod setup**
> **Make sure you have docker installed and env vars setup as described in setting up dev environment section above**
```sh
git clone https://github.com/VVIP-Kitchen/boo.git;
cd boo;
docker compose up --build -d;
```
