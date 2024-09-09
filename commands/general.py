import io
import csv
import requests
from discord import File, Embed, SelectOption, ButtonStyle
import random
import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from services.llm_service import WorkersService
from services.api_service import ApiService
from services.tenor_service import TenorService
from utils.config import server_contexts, user_memory


class GeneralCommands(commands.Cog):
  """
  Cog for general-purpose commands.
  """

  def __init__(self, bot: commands.Bot) -> None:
    """
    Initialize the GeneralCommands cog.

    Args:
      bot (commands.Bot): The Discord bot instance.
    """

    self.bot = bot
    self.llm_service = WorkersService()
    self.tenor_service = TenorService()
    self.api_service = ApiService()
    self.posts = self.load_posts()


  def load_posts(self):
    posts = []
    with open('Discourse_Posts_06_09_24.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append(row)
    return posts

  @commands.hybrid_command(name="discourse", description="Search for posts from Discourse")
  async def search_posts(self, ctx: commands.Context, keyword: str) -> None:
        if ctx.guild is not None and ctx.channel.name != "chat":
            await ctx.send("Ping me in <#1272840978277072918> to talk", ephemeral=True)
            return

        if ctx.interaction:
            await ctx.defer()
        else:
            await ctx.typing()
        
        matching_posts = [post for post in self.posts if keyword.lower() in post['Title'].lower()]

        if not matching_posts:
            await ctx.send(f"No posts found matching the keyword: {keyword}")
            return

        posts_per_page = 10
        pages = [matching_posts[i:i + posts_per_page] for i in range(0, len(matching_posts), posts_per_page)]
        current_page = 0

        async def update_embed(page):
            embed = Embed(title="Discourse Posts", description=f"Search results for '{keyword}'\n\n\n")
            for post in pages[page]:
                # Use Discord's native linking
                embed.description+= f"**[{post['Title'][:100]}]({post['Post Link']})**\n Tags: {post['Tags'][:100]}\n\n"
                
            embed.set_footer(text=f"Page {page + 1}/{len(pages)} • Total posts: {len(matching_posts)}")
            return embed

        async def button_callback(interaction, change):
            nonlocal current_page
            current_page = (current_page + change) % len(pages)
            await interaction.response.edit_message(embed=await update_embed(current_page), view=create_view())

        def create_view():
            view = View()
            prev_button = Button(style=ButtonStyle.gray, label="Previous")
            next_button = Button(style=ButtonStyle.gray, label="Next")
            
            prev_button.callback = lambda i: button_callback(i, -1)
            next_button.callback = lambda i: button_callback(i, 1)
            
            view.add_item(prev_button)
            view.add_item(next_button)
            return view

        initial_embed = await update_embed(current_page)
        initial_view = create_view()
        await ctx.send(embed=initial_embed, view=initial_view)
    

  

  @commands.hybrid_command(name="info", description="Get to know the spooktacular Boo!")
  async def respond_with_info(self, ctx):
      bot_avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else ctx.bot.user.default_avatar.url
      
      # Create the main embed
      embed = discord.Embed(title="Boo's Haunted House of Info :ghost:", color=discord.Color.purple())
      embed.set_author(name="Boo", icon_url=bot_avatar)
      embed.set_footer(text="Crafted with :cosy: by enderboi | React with 👻 for a spooky surprise!")
      
      # Randomize greeting
      greetings = [
          "BOO! Did I scare ya? :evil:",
          "Welcome to my crib! :cosy:",
          "Sup, mere mortal? Ready to get spooked? :kekfast:",
          "Greetings, human! Let's get :derp:y!",
      ]
      embed.description = random.choice(greetings)

      # Fun facts about Boo
      fun_facts = [
          "I'm a :ghost:, but I'm scared of :mouse: mice!",
          "I can speak in :regional_indicator_e: :regional_indicator_m: :regional_indicator_o: :regional_indicator_j: :regional_indicator_i:!",
          "I once tried to haunt a :computer:, but it ghosted me first!",
          "My favorite food is :spaghetti: boo-sta!",
          "I'm fluent in :scroll: JavaScript, Python, and Boo-lean logic!",
      ]
      embed.add_field(name="Boo-tiful Facts", value="\n".join(fun_facts), inline=False)

      # Boo's capabilities
      capabilities = (
          ":joystick: Drop sick gaming knowledge\n"
          ":computer: Debug your code (and add bugs for fun)\n"
          ":movie_camera: Quote every movie ever (even the bad ones)\n"
          ":cook: Share recipes that are to die for\n"
          ":soccer: Ref your sports arguments\n"
          ":nerd: Engage in 3 AM philosophical debates\n"
          ":zany_face: Troll you when you least expect it :kekpoint:"
      )
      embed.add_field(name="What I Can Boo For You", value=capabilities, inline=False)

      # Bot info with a twist
      bot_info = (
          f"Bot ID: ||{ctx.bot.user.id}|| (Shhh, it's a secret!)\n"
          f"Bot Owner: <@345546510013825033> :crown: (AKA 'The Exorcist')\n"
          f"Prefix: `{ctx.prefix}` (Use it wisely, or I'll :angy:)\n"
          "Source: [GitHub](https://github.com/VVIP-Kitchen/boo) :evil: (Warning: May contain traces of ectoplasm)"
      )
      embed.add_field(name="The Ghostly Deets", value=bot_info, inline=False)

      # Interactive challenge
      challenges = [
          "Quick! Tell me a joke that'll make a ghost laugh!",
          "If you can solve this riddle, I'll give you a virtual cookie: What has keys but no locks, space but no room, and you can enter but not go in?",
          "I bet you can't type 'Boo is the coolest bot' backwards in 10 seconds!",
          "Let's play rock-paper-scissors! Reply with your choice!",
      ]
      embed.add_field(name="Spooky Challenge", value=random.choice(challenges), inline=False)

      # Easter egg
      embed.add_field(name="P.S.", value="||Did you know that if you say 'deez nuts' three times in front of a mirror, I'll appear and... actually, nevermind. :hmmge:||", inline=False)

      message = await ctx.send(embed=embed)
      await message.add_reaction('👻')

  @commands.Cog.listener()
  async def on_reaction_add(self, reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) == '👻' and reaction.message.author == self.bot.user:
        spooky_messages = [
            "BOO! Did I getcha? :evil:",
            "You've awakened the great Boo! Prepare for... a dad joke!",
            "A ghost appeared! Oh wait, it's just me. :kekfast:",
            "You summoned me? I was in the middle of haunting my keyboard!",
            ":deez: :nuts: (I couldn't resist, sorry not sorry)",
        ]
        await reaction.message.channel.send(random.choice(spooky_messages))

    



  @commands.hybrid_command(name="greet", description="Greets the user")
  async def greet(self, ctx: commands.Context) -> None:
    """
    Greet the user who invoked the command.

    Args:
      ctx (commands.Context): The invocation context.
    """
    if ctx.guild is not None:
      if ctx.channel.name == "chat":
        await ctx.send(f"{ctx.author} How can I assist you today? 👀")
      else:
        await ctx.send(
          f"{ctx.author} How can I assist you today? 👀\nBut ping me in <#1272840978277072918> to talk",
          ephemeral=True,
        )
    else:
      await ctx.send(f"{ctx.author} How can I assist you today? 👀")


  @commands.hybrid_command(name="ping" , description="Pings the bot")
  async def respond_with_ping(self, ctx):
      ping = self.bot.latency * 1000
      embed = discord.Embed(title="Ping", description=f"The ping of the bot is {ping:.2f}ms", color=0x7615D1)
      await ctx.send(embed=embed)


  @commands.hybrid_command(name="bonk", description="Bonks a user")
  async def bonk(self, ctx: commands.Context, member: discord.Member) -> None:
    async with ctx.typing():
      bonk_gif = random.choice(self.tenor_service.search())
      await ctx.send(
        content=f"<@{ctx.author.id}> has bonked <@{member.id}> {bonk_gif['url']}"
      )


  @commands.hybrid_command(
    name="imagine", description="Generates an image from a prompt"
  )
  async def imagine(self, ctx: commands.Context, *, prompt: str) -> None:
    """
    Generate an image based on the given prompt.

    Args:
      ctx (commands.Context): The invocation context.
      prompt (str): The prompt for image generation.
    """
    if ctx.guild is not None and ctx.channel.name != "chat":
      await ctx.send("Ping me in <#1272840978277072918> to talk", ephemeral=True)
      return

    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()

    result = self.llm_service.generate_image(prompt)
    server_id = f"DM_{ctx.author.id}" if ctx.guild is None else ctx.guild.id
    user_id = str(ctx.author.id)

    if isinstance(result, io.BytesIO):
      file = File(result, "output.png")
      await ctx.send(file=file)

      ### Add that to user's context
      server_contexts[server_id].append(
        {
          "role": "user",
          "content": f"{ctx.author.name} (aka {ctx.author.display_name}) used the /imagine command to generate an image with the prompt: {prompt}",
        }
      )
      server_contexts[server_id].append(
        {
          "role": "assistant",
          "content": f"I generated an image based on the prompt: '{prompt}'. The image was successfully created and sent to the chat.",
        }
      )

      ### Add that to user's memory
      if server_id not in user_memory[user_id]:
        user_memory[user_id][server_id] = []

      user_memory[user_id][server_id].append(
        {
          "type": "image",
          "prompt": prompt,
          "timestamp": ctx.message.created_at.isoformat(),
        }
      )
    else:
      await ctx.send(result)

      ### Add to context
      server_contexts[server_id].append(
        {
          "role": "user",
          "content": f"{ctx.author.name} (aka {ctx.author.display_name}) attempted to use the /imagine command with the prompt: {prompt}, but there was an error.",
        }
      )
      server_contexts[server_id].append(
        {
          "role": "assistant",
          "content": f"There was an error generating the image for the prompt: '{prompt}'. The error message was: {result}",
        }
      )

  @commands.cooldown(10, 60)
  @commands.hybrid_command(name="skibidi", description="You are my skibidi")
  async def skibidi(self, ctx: commands.Context) -> None:
    """
    Post O Skibidi RE

    Args:
      ctx (commands.Context): The invocation context.
    """
    await ctx.send(f"SKIBIDI 😍\nhttps://youtu.be/smQ57m7mjSU")

  @commands.hybrid_command(name="weather", description="Get the weather")
  async def weather(self, ctx: commands.Context, location: str) -> None:
    """
    Get the weather for a location.

    Args:
      ctx (commands.Context): The invocation context.
      location (str): The location for which to get the weather.
    """
    if ctx.guild is not None and ctx.channel.name != "chat":
      await ctx.send("Ping me in <#1272840978277072918> to talk", ephemeral=True)
      return

    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()
    result = self.api_service.weather_info(location)
    await ctx.send(result)



async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """

  await bot.add_cog(GeneralCommands(bot))
