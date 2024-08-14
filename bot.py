import io
import aiohttp
import discord
import requests
from PIL import Image, ImageOps
from discord.ext import commands
from config import (
    CONTEXT_LIMIT,
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_WORKERS_AI_API_KEY,
    DISCORD_TOKEN,
    get_time_based_greeting,
    server_lore,
    server_contexts,
    user_memory,
)

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="", intents=intents)


### Reference: https://github.com/craigsdennis/image-model-streamlit-workers-ai/blob/main/pages/3_%F0%9F%91%81%EF%B8%8F_Seeing.py
def image_to_int_array(image, format="PNG"):
    """Current Workers AI REST API consumes an array of unsigned 8 bit integers"""
    bytes = io.BytesIO()
    image.save(bytes, format=format)
    return list(bytes.getvalue())


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    server_id = message.guild.id
    prompt = str(message.content).strip()

    img = None
    if len(message.attachments) >= 0:
        img_url = message.attachments[0].url

        async with aiohttp.ClientSession() as session:
            async with session.get(img_url) as res:
                blob = await res.read()
                img = Image.open(blob)
                img = ImageOps.contain(img, (600, 600))

                if img is not None:
                    try:
                        response = requests.post(
                            f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/llava-hf/llava-1.5-7b-hf",
                            headers={
                                "Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"
                            },
                            json={"prompt": messages, "image": image_to_int_array(img)},
                        )
                        response.raise_for_status()
                        result = response.json()
                        bot_response = str(result["result"]["response"])
                        print(bot_response)
                        await message.channel.send(bot_response)
                        return
                    except requests.RequestException as e:
                        print(f"API request failed: {e}")
                        bot_response = "Sorry, I'm having trouble thinking right now. Can you try again later?"
                    except KeyError:
                        print("Unexpected API response format")
                        bot_response = "I'm a bit confused. Can you rephrase that?"

    if "cheen tapak dam dam".strip().lower() in prompt:
        await message.channel.send("https://tenor.com/sMEecgRE0sl.gif")
        return

    if prompt.lower().startswith("reset chat"):
        server_contexts[server_id] = []
        await message.channel.send("Context reset! Starting a new conversation.")
        return

    ### Handle user mentions
    if "<@" in prompt:
        mentions = message.mentions
        for mention in mentions:
            user_id = mention.id
            username = mention.name
            prompt = prompt.replace(f"<@{user_id}>", f"{username}")

    if not message.author.bot and len(prompt) != 0:
        ### Check if the user wants to share some information
        if prompt.lower().startswith("remember that"):
            fact = prompt[len("remember that") :].strip()
            user_memory[message.author.id]["fact"] = fact
            await message.channel.send(f"Got it! I'll remember that {fact}.")
            return

        ### Check if the user wants to recall something
        if prompt.lower().startswith("what do you remember about me"):
            fact = user_memory.get(message.author.id, {}).get(
                "fact", "I don't remember anything specific about you yet."
            )
            await message.channel.send(f"Here's what I remember: {fact}")
            return

        ### Build the context for the conversation
        server_contexts[server_id].append(
            {
                "role": "user",
                "content": message.author.name
                + " (aka "
                + message.author.display_name
                + ")"
                + " said: "
                + prompt,
            }
        )
        messages = [{"role": "system", "content": server_lore}] + server_contexts[
            server_id
        ]

        try:
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct-awq",
                headers={"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"},
                json={"messages": messages},
            )
            response.raise_for_status()
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

        ### Add the bot's response to the conversation context
        server_contexts[server_id].append(
            {"role": "assistant", "content": bot_response}
        )
        await message.channel.send(bot_response)

        ### Reset context if it gets too large
        if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
            server_contexts[server_id] = []
            await message.channel.send("Context reset! Starting a new conversation.")

    await bot.process_commands(message)


@bot.command(name="hello")
async def greet(ctx):
    greeting = get_time_based_greeting()
    await ctx.send(f"{greeting}, {ctx.author.name}! How can I assist you today?")


bot.run(DISCORD_TOKEN)
