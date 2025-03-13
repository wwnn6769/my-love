import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path="my_discord_bot/.env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
COMMAND_CHANNEL_ID = 1345084711302729839
WELCOME_CHANNEL_ID = 1345063015203995700
REACTION_ROLE_CHANNEL_ID = 1345086945876905994

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
