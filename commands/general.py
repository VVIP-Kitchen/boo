import io
from discord import File
from discord.ext import commands
from services.llm_service import WorkersService
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
  

  @commands.hybrid_command(name="info", description="Ge    t to know the spooktacular Boo!")
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


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """

  await bot.add_cog(GeneralCommands(bot))
