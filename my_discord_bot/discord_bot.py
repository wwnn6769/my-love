import os
import re
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 導入各功能 helper
from src.nlp.basic_translator import translate_text
from src.nlp.text_to_speech import generate_speech
from src.nlp.transpeak import transpeak_text
from src.data_logging.logging_module import logger as task_logger
from src.video.edit_video import clip_video
from src.generation.generate_image import generate_image
from src.generation.generate_voice import generate_voice
from src.generation.generate_video import generate_video

load_dotenv()  # 從 .env 載入環境變數
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("DISCORD_PREFIX", "!")

# 自訂義個性與關鍵字規則 (可擴充)
COMMAND_PATTERNS = {
    "translate": re.compile(r".*翻譯(功能)?\s*(.+?)\s*到\s*(\S+)", re.IGNORECASE),
    "transpeak": re.compile(r".*翻譯(結果)?\s*到\s*(\S+)", re.IGNORECASE),
    "clip": re.compile(r".*剪輯\s+(\S+)\s+到\s+(\S+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)", re.IGNORECASE),
    "generate_image": re.compile(r".*生成圖像", re.IGNORECASE),
    "generate_voice": re.compile(r".*生成語音", re.IGNORECASE),
    "generate_video": re.compile(r".*生成影片", re.IGNORECASE),
}
# 假設其他關鍵字：若訊息未匹配任何指令，視為一般閒聊

class DiscordBot(commands.Bot):
    def __init__(self, logger: logging.Logger):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # 會員事件（歡迎新人）
        super().__init__(command_prefix=PREFIX, intents=intents)
        self.logger = logger

        # 註冊預設指令（前綴形式依然可用）
        self.add_command(self.ping)
        self.add_command(self.translate_cmd)
        self.add_command(self.tts_cmd)
        self.add_command(self.clip_cmd)
        self.add_command(self.log_cmd)
        self.add_command(self.transpeak_cmd)
        self.add_command(self.generate_image_cmd)
        self.add_command(self.generate_voice_cmd)
        self.add_command(self.generate_video_cmd)

    async def on_ready(self):
        self.logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        print(f"Bot is ready! Logged in as {self.user}")

    async def on_member_join(self, member):
        # 歡迎新人，並在特定頻道發送歡迎訊息（頻道 ID 請自行設定）
        welcome_channel_id = 123456789012345678  # 請替換為實際頻道 ID
        channel = self.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"歡迎 {member.mention} 加入！請閱讀頻道公告。")

    async def on_reaction_add(self, reaction, user):
        # 根據特定表情自動分配身分組（不可逆），僅在特定頻道執行
        assign_channel_id = 234567890123456789  # 請替換
        target_role_id = 345678901234567890     # 請替換
        if reaction.message.channel.id == assign_channel_id and str(reaction.emoji) == "✅":
            guild = reaction.message.guild
            role = guild.get_role(target_role_id)
            member = guild.get_member(user.id)
            if role and member:
                await member.add_roles(role)
                await reaction.message.channel.send(f"{member.mention} 已獲得 {role.name} 身分組。")

    async def on_message(self, message):
        # 避免回覆自己或其他機器人訊息
        if message.author.bot:
            return

        # 優先處理以前綴開頭的指令
        await self.process_commands(message)

        # 若非以指令前綴發送，進行自然語言解析
        content = message.content.strip()
        # 檢查是否匹配翻譯指令（例： "幫我翻譯 我愛你 到日語" ）
        match = COMMAND_PATTERNS["translate"].match(content)
        if match:
            text_to_translate = match.group(2)
            target_lang = match.group(3)
            try:
                translation = translate_text(text_to_translate, dest=target_lang)
                await message.channel.send(f"翻譯結果：{translation}")
            except Exception as e:
                self.logger.exception("NL 轉換翻譯錯誤：%s", e)
                await message.channel.send("翻譯失敗。")
            return

        # 檢查 Transpeak 指令（例： "翻譯結果到韓語" ）
        match = COMMAND_PATTERNS["transpeak"].match(content)
        if match:
            target_lang = match.group(2)
            try:
                # 使用前一次翻譯結果（此處示範，實際應儲存上下文）
                # 為示範，直接回傳 "Hello" 經翻譯再 TTS
                output_file = "transpeak.mp3"
                transpeak_text("Hello", target_lang=target_lang, tts_lang=target_lang, output_file=output_file)
                await message.channel.send(file=discord.File(output_file))
            except Exception as e:
                self.logger.exception("NL Transpeak 錯誤：%s", e)
                await message.channel.send("Transpeak 失敗。")
            return

        # 檢查影片剪輯指令（例： "剪輯 D:\input.mp4 到 D:\output.mp4 10 20"）
        match = COMMAND_PATTERNS["clip"].match(content)
        if match:
            input_video = match.group(1)
            output_video = match.group(2)
            start_time = float(match.group(3))
            end_time = float(match.group(4))
            try:
                result, process_info = clip_video(input_video, output_video, start_time, end_time)
                if result:
                    await message.channel.send(f"影片剪輯完成：{output_video}\n剪輯過程：{process_info}")
                else:
                    await message.channel.send("影片剪輯失敗。")
            except Exception as e:
                self.logger.exception("NL 剪輯錯誤：%s", e)
                await message.channel.send("影片剪輯失敗。")
            return

        # 檢查生成圖像、語音、影片指令（例："生成圖像"、"生成語音"、"生成影片"）
        if COMMAND_PATTERNS["generate_image"].match(content):
            output_file = "generated_image.png"
            if generate_image(content, output_file):
                await message.channel.send(file=discord.File(output_file))
            else:
                await message.channel.send("圖像生成失敗。")
            return

        if COMMAND_PATTERNS["generate_voice"].match(content):
            output_file = "generated_voice.mp3"
            if generate_voice(content, output_file):
                await message.channel.send(file=discord.File(output_file))
            else:
                await message.channel.send("語音生成失敗。")
            return

        if COMMAND_PATTERNS["generate_video"].match(content):
            output_file = "generated_video.mp4"
            if generate_video(content, output_file):
                await message.channel.send(file=discord.File(output_file))
            else:
                await message.channel.send("影片生成失敗。")
            return

        # 若無匹配任何功能，回覆簡易聊天（這邊可根據需求進行更複雜的對話處理）
        await message.channel.send("很抱歉，我不太明白你的意思。請使用明確的功能指令。")

    # 以下為傳統前綴指令（也可透過自然語言觸發）
    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command(name="translate")
    async def translate_cmd(self, ctx, *, text: str):
        try:
            translation = translate_text(text, dest='en')
            await ctx.send(f"翻譯結果：{translation}")
        except Exception as e:
            self.logger.exception("翻譯錯誤：%s", e)
            await ctx.send("翻譯失敗。")

    @commands.command(name="tts")
    async def tts_cmd(self, ctx, *, text: str):
        try:
            output_file = "speech.mp3"
            generate_speech(text, lang="en", output_file=output_file)
            await ctx.send(file=discord.File(output_file))
        except Exception as e:
            self.logger.exception("TTS 錯誤：%s", e)
            await ctx.send("語音生成失敗。")

    @commands.command(name="clip")
    async def clip_cmd(self, ctx, input_video: str, output_video: str, start_time: float, end_time: float):
        try:
            result, process_info = clip_video(input_video, output_video, start_time, end_time)
            if result:
                await ctx.send(f"影片剪輯完成，輸出：{output_video}\n剪輯過程：{process_info}")
            else:
                await ctx.send("影片剪輯失敗。")
        except Exception as e:
            self.logger.exception("影片剪輯錯誤：%s", e)
            await ctx.send("影片剪輯失敗。")

    @commands.command(name="log")
    async def log_cmd(self, ctx, *, message: str):
        try:
            task_logger.info(message)
            await ctx.send("日誌已更新。")
        except Exception as e:
            self.logger.exception("日誌錯誤：%s", e)
            await ctx.send("日誌更新失敗。")

    @commands.command(name="transpeak")
    async def transpeak_cmd(self, ctx, *, text: str):
        try:
            output_file = "transpeak.mp3"
            transpeak_text(text, target_lang='en', tts_lang='en', output_file=output_file)
            await ctx.send(file=discord.File(output_file))
        except Exception as e:
            self.logger.exception("Transpeak 錯誤：%s", e)
            await ctx.send("Transpeak 失敗。")

    @commands.command(name="generate_image")
    async def generate_image_cmd(self, ctx, *, prompt: str):
        output_file = "generated_image.png"
        if generate_image(prompt, output_file):
            await ctx.send(file=discord.File(output_file))
        else:
            await ctx.send("圖像生成失敗。")

    @commands.command(name="generate_voice")
    async def generate_voice_cmd(self, ctx, *, prompt: str):
        output_file = "generated_voice.mp3"
        if generate_voice(prompt, output_file):
            await ctx.send(file=discord.File(output_file))
        else:
            await ctx.send("語音生成失敗。")

    @commands.command(name="generate_video")
    async def generate_video_cmd(self, ctx, *, prompt: str):
        output_file = "generated_video.mp4"
        if generate_video(prompt, output_file):
            await ctx.send(file=discord.File(output_file))
        else:
            await ctx.send("影片生成失敗。")

    def run_bot(self):
        if not TOKEN:
            self.logger.error("DISCORD_TOKEN 未設定！")
            return
        super().run(TOKEN)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot = DiscordBot(logger=logging.getLogger("DiscordBot"))
    bot.run_bot()
