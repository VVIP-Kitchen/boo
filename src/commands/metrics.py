from discord.ext import commands
from services.db_service import DBService
from services.task_queue_service import TaskQueueService
from services.meilisearch_service import MeilisearchService


class MetricsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_service = DBService()
        self.task_queue_service = TaskQueueService()
        self.meilisearch_service = MeilisearchService()

    @commands.hybrid_command(name="metrics", help="Get bot metrics")
    @commands.is_owner()
    async def metrics(self, ctx):
        """Get bot metrics"""
        task_queue_info = self.task_queue_service.get_queue_info()
        meilisearch_stats = self.meilisearch_service.get_stats()

        await ctx.send(
            f"""
**Task Queue Info:**
- Name: {task_queue_info.get('name')}
- Count: {task_queue_info.get('count')}
- Failed Count: {task_queue_info.get('failed_count')}
- Finished Count: {task_queue_info.get('finished_count')}
- Started Count: {task_queue_info.get('started_count')}

**Meilisearch Stats:**
- Total Documents: {meilisearch_stats.get('total_documents')}
- Is Indexing: {meilisearch_stats.get('is_indexing')}
            """
        )


async def setup(bot):
    await bot.add_cog(MetricsCog(bot))
