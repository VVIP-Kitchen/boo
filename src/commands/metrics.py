from discord.ext import commands
from services.meilisearch_service import MeilisearchService


class MetricsCog(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.meilisearch_service = MeilisearchService()

  @commands.hybrid_command(name="meilisearch-metrics", help="Get Meilisearch index stats")
  @commands.is_owner()
  async def metrics(self, ctx):
    stats = self.meilisearch_service.get_stats()
    await ctx.send(
      "**Meilisearch Stats:**\n"
      f"- Total Documents: {stats.get('total_documents')}\n"
      f"- Is Indexing: {stats.get('is_indexing')}\n\n"
      "-# Background task metrics live in the Temporal UI."
    )


async def setup(bot):
  await bot.add_cog(MetricsCog(bot))
