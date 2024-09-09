import io
import csv
import requests
from discord import File, Embed, SelectOption, ButtonStyle
from discord.ext import commands
from discord.ui import Select, View, Button
from services.llm_service import WorkersService
from services.api_service import ApiService
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
