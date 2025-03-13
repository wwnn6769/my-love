import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from bot_setup import bot, TOKEN

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import tracemalloc
    tracemalloc.start()

    import asyncio
    asyncio.run(main())
