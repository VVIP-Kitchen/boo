import discord
from datetime import datetime
from discord.ext import commands
from services.db_service import DBService
from services.async_caller_service import to_thread


class MemoryManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_service = DBService()

    @commands.hybrid_group(name="memory", description="Manage your memories")
    async def memory_group(self, ctx: commands.Context) -> None:
        """Memory management commands."""
        pass

    @memory_group.command(name="list", description="View stored memories")
    async def list_memories(
        self, ctx: commands.Context, user: discord.Member = None
    ) -> None:
        """List memories for a user."""
        await ctx.defer()

        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        target_user = user or ctx.author

        try:
            memories = await to_thread(
                self.db_service.get_memories, str(ctx.guild.id), str(target_user.id)
            )

            if not memories:
                embed = discord.Embed(
                    title="🧠 No Memories",
                    description=f"No memories stored for **{target_user.display_name}** yet.",
                    color=0x7615D1,
                    timestamp=datetime.now(),
                )
                embed.set_thumbnail(url=target_user.display_avatar.url)
                return await ctx.send(embed=embed)

            embed = discord.Embed(
                title=f"🧠 Memories for {target_user.display_name}",
                description=f"Found **{len(memories)}** memory(s)",
                color=0x7615D1,
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)

            for idx, memory in enumerate(memories, 1):
                fact = memory.get("fact", "Unknown")
                memory_id = memory.get("id", "?")
                created_at = memory.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_str = f"<t:{int(dt.timestamp())}:R>"
                    except Exception:
                        created_str = created_at
                else:
                    created_str = "Unknown"

                embed.add_field(
                    name=f"#{idx} (ID: {memory_id})",
                    value=f"{fact}\n-# Stored {created_str}",
                    inline=False,
                )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to fetch memories: {str(e)}",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)

    @memory_group.command(name="delete", description="Delete a memory by ID")
    async def delete_memory(self, ctx: commands.Context, memory_id: int) -> None:
        """Delete a specific memory."""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        try:
            memory = await to_thread(self.db_service.get_memory_by_id, memory_id)

            if not memory:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Memory with ID `{memory_id}` not found.",
                    color=0xFF0000,
                )
                return await ctx.send(embed=embed)

            if memory.get("author_id") != str(ctx.author.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You can only delete your own memories.",
                    color=0xFF0000,
                )
                return await ctx.send(embed=embed)

            success = await to_thread(self.db_service.delete_memory, memory_id)

            if success:
                embed = discord.Embed(
                    title="✅ Deleted",
                    description=f"Memory #{memory_id} has been deleted.",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to delete memory. Please try again.",
                    color=0xFF0000,
                )
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to delete memory: {str(e)}",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)

    @memory_group.command(name="edit", description="Edit a memory fact")
    async def edit_memory(
        self, ctx: commands.Context, memory_id: int, *, new_fact: str
    ) -> None:
        """Edit a specific memory."""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        if not new_fact.strip():
            embed = discord.Embed(
                title="❌ Error",
                description="The new fact cannot be empty.",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        try:
            memory = await to_thread(self.db_service.get_memory_by_id, memory_id)

            if not memory:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Memory with ID `{memory_id}` not found.",
                    color=0xFF0000,
                )
                return await ctx.send(embed=embed)

            if memory.get("author_id") != str(ctx.author.id):
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You can only edit your own memories.",
                    color=0xFF0000,
                )
                return await ctx.send(embed=embed)

            success = await to_thread(self.db_service.update_memory, memory_id, new_fact.strip())

            if success:
                embed = discord.Embed(
                    title="✅ Updated",
                    description=f"Memory #{memory_id} has been updated.",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )
                embed.add_field(name="New fact", value=new_fact.strip(), inline=False)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to update memory. Please try again.",
                    color=0xFF0000,
                )
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to update memory: {str(e)}",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)

    @memory_group.command(name="search", description="Search through memories")
    async def search_memories(
        self, ctx: commands.Context, user: discord.Member = None, *, query: str
    ) -> None:
        """Search through memories by content."""
        await ctx.defer()

        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This command can only be used in a server",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        if not query.strip():
            embed = discord.Embed(
                title="❌ Error",
                description="Search query cannot be empty.",
                color=0xFF0000,
            )
            return await ctx.send(embed=embed)

        target_user = user or ctx.author

        try:
            memories = await to_thread(
                self.db_service.search_memories,
                str(ctx.guild.id),
                query.strip(),
                str(target_user.id),
            )

            if not memories:
                embed = discord.Embed(
                    title="🔍 No Results",
                    description=f"No memories found matching **\"{query}\"** for {target_user.display_name}.",
                    color=0x7615D1,
                    timestamp=datetime.now(),
                )
                embed.set_thumbnail(url=target_user.display_avatar.url)
                return await ctx.send(embed=embed)

            embed = discord.Embed(
                title=f"🔍 Search Results for \"{query}\"",
                description=f"Found **{len(memories)}** matching memory(ies) for **{target_user.display_name}**",
                color=0x7615D1,
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)

            for idx, memory in enumerate(memories, 1):
                fact = memory.get("fact", "Unknown")
                memory_id = memory.get("id", "?")
                author_name = memory.get("author_name", "Unknown")
                created_at = memory.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_str = f"<t:{int(dt.timestamp())}:R>"
                    except Exception:
                        created_str = created_at
                else:
                    created_str = "Unknown"

                embed.add_field(
                    name=f"#{idx} (ID: {memory_id}) by {author_name}",
                    value=f"{fact}\n-# Stored {created_str}",
                    inline=False,
                )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to search memories: {str(e)}",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemoryManagementCog(bot))
