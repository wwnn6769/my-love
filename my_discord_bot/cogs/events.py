# cogs/events.py
import discord
from discord.ext import commands

from utils.config import WELCOME_CHANNEL_ID, COMMAND_CHANNEL_ID, REACTION_ROLE_CHANNEL_ID

class EventHandlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """新成員加入時發送歡迎訊息"""
        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            try:
                embed = discord.Embed(
                    title="🎊 歡迎新朋友！",
                    description=f"{member.mention} 加入了我們的伺服器！\n\n"
                                f"• 請先閱讀 <#{COMMAND_CHANNEL_ID}> 的規則\n"
                                f"• 前往 <#{REACTION_ROLE_CHANNEL_ID}> 選擇身分組",
                    color=0xFFD700
                )
                # 若成員沒有自訂大頭貼則使用預設大頭貼
                avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
                embed.set_thumbnail(url=avatar_url)
                await welcome_channel.send(embed=embed)
            except Exception as e:
                print(f"發送歡迎訊息失敗：{e}")

def setup(bot):
    bot.add_cog(EventHandlers(bot))
