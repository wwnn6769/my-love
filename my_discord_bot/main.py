# main.py
import os
import time
import discord
from discord.ext import commands

from utils.config import TOKEN, COMMAND_CHANNEL_ID

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 自動載入 cogs 資料夾內的所有 Cog 模組
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    print(f"\n{'='*40}")
    print(f'登入身份：{bot.user.name} ({bot.user.id})')
    print(f'指令頻道：{COMMAND_CHANNEL_ID}')
    print(f'就緒時間：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    print(f"{'='*40}\n")
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="!help 查看指令"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    from discord.ext import commands
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ 未知指令，輸入 `!help` 查看可用指令")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 缺少必要參數：`{error.param.name}`")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        await ctx.send(f"⚠️ 發生未處理錯誤：```{str(error)}```")
        raise error

if __name__ == "__main__":
    print("正在初始化機器人...")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token 無效或登入失敗")
    except KeyboardInterrupt:
        print("\n正在安全關閉機器人...")
        import asyncio
        async def disconnect_voice_clients():
            for vc in bot.voice_clients:
                await vc.disconnect()
            print("已斷開所有語音連接")
        asyncio.run(disconnect_voice_clients())
    finally:
        print("機器人進程已終止")
