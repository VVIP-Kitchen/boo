import io
import csv
import requests
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
    self.posts = self.load_posts()


  def load_posts(self):
    posts = []
    with open('Discourse_Posts_06_09_24.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append(row)
    return posts

  @commands.hybrid_command(name="Discourse", description="Search for posts from Discourse")
  async def search_posts(self, ctx: commands.Context, keyword: str) -> None:
        """
        Search for posts by keyword and provide a list of matching titles.

        Args:
          ctx (commands.Context): The invocation context.
          keyword (str): The keyword to search for in post titles.
        """
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

        options = [
            SelectOption(label=post['Title'][:100], value=str(i))  # Truncate title if too long
            for i, post in enumerate(matching_posts[:25])  # Limit to 25 options due to Discord's limit
        ]

        select = Select(placeholder="Choose a post to view", options=options)

        async def select_callback(interaction):
            selected_post = matching_posts[int(select.values[0])]
            embed = Embed(title=selected_post['Title'], url=selected_post['Post Link'])
            embed.add_field(name="Tags", value=selected_post['Tags'])
            await interaction.response.send_message(embed=embed)

        select.callback = select_callback
        view = View()
        view.add_item(select)

        await ctx.send(f"Found {len(matching_posts)} posts matching '{keyword}'. Please select one:", view=view)


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

  @commands.hybrid_command(name="Weather", description="Get the weather")
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

    response = requests.get(
      "https://api.tomorrow.io/v4/weather/realtime",
      params={"location": location, "apikey": "ha29HDAuTNyVmbZBC3G3dXunQLfrYTqi"},
    )
    data = response.json()

    if "error" in data:
      await ctx.send(f"Error: {data['error']['message']}")
    else:
      weather = data["weather"]["conditions"]["temperature"]["value"]
      await ctx.send(f"The temperature in {location} is {weather}°C")


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """

  await bot.add_cog(GeneralCommands(bot))
