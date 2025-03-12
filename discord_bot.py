import discord
from discord.ext import commands
from TTS.api import TTS
import os
import json
import time
import torch.serialization
from TTS.utils.radam import RAdam
from collections import defaultdict
from argostranslate import translate
import yt_dlp
from pydub import AudioSegment
from pydub.silence import detect_silence
import asyncio
import tempfile
from discord import utils
import shutil
import re

# -------------------- 基本設定 --------------------
# 請務必將 Discord Bot Token 設定為環境變數（或自行填入，但注意安全）
TOKEN = "MTM0NTAyNjY4NzkzNDQwMjYwMQ.G7UdtA.rW6ZxfMcDo57Em1wykzZHVeIdEYeV2EvksyyeI"

COMMAND_CHANNEL_ID = 1345084711302729839   # 指令使用頻道
WELCOME_CHANNEL_ID = 1345063015203995700    # 歡迎新成員的頻道
REACTION_ROLE_CHANNEL_ID = 1345086945876905994  # 訂選（反應角色）頻道

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- 全域變數 --------------------
# 播放清單隊列：key 為 guild id，value 為 (audio_file, speed, url) 列表
music_queues = defaultdict(list)
# 控制面板訊息，每個伺服器一則（新版：每次更新前先刪除舊的）
control_messages = {}
# 預設播放速度，每個伺服器一個，預設 1.0
default_speed = {}
# 關於 !play 指令的回覆訊息，僅保留最新 3 則
play_replies = defaultdict(list)
# 儲存目前正在播放的曲目資訊：key 為 guild id，value 為 (audio_file, url)
current_track_info = {}

# 設定下載儲存目錄（請修改為你的磁碟位置，如 D:\Assistant\dc music ）
BASE_DIR = r"D:\Assistant\dc music"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# -------------------- 全域 yt_dlp 選項 --------------------
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True}
# 若存在 cookies.txt 則自動加入 (用於繞過 YouTube 年齡限制)
if os.path.exists("cookies.txt"):
    YDL_OPTIONS['cookiefile'] = "cookies.txt"

# -------------------- TTS 功能 --------------------
voice_map = {
    "溫柔": "tts_models/zh-CN/baker/tacotron2-DDC-GST",
    "低沉": "tts_models/en/ljspeech/glow-tts",
    "動漫": "tts_models/en/vctk/vits",
    "機器人": "tts_models/en/ljspeech/glow-tts",
    "正常": "tts_models/zh-CN/baker/tacotron2-DDC-GST",
    "法語": "tts_models/fr/css10/vits",
    "Doux": "tts_models/fr/css10/vits",
    "Profond": "tts_models/fr/css10/vits",
    "Robotique": "tts_models/fr/css10/vits"
}

VOICE_SETTINGS_FILE = "voice_settings.json"

def load_voice_settings():
    if os.path.exists(VOICE_SETTINGS_FILE):
        with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_voice_settings(settings):
    with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4, ensure_ascii=False)

user_voice_settings = load_voice_settings()
tts_instances = {}

def in_command_channel():
    async def predicate(ctx):
        if ctx.channel.id != COMMAND_CHANNEL_ID:
            await ctx.send(f"請到 <#{COMMAND_CHANNEL_ID}> 使用指令！")
            return False
        return True
    return commands.check(predicate)

@bot.command()
@in_command_channel()
async def setvoice(ctx, voice_type: str):
    """設定使用者 TTS 語音風格"""
    user_id = str(ctx.author.id)
    if voice_type not in voice_map:
        await ctx.send(f"⚠️ 無效的語音風格 `{voice_type}`，我目前支援：{', '.join(voice_map.keys())}")
        return
    user_voice_settings[user_id] = voice_type
    save_voice_settings(user_voice_settings)
    await ctx.send(f"✅ **已設定你的語音風格為 `{voice_type}`**")

@bot.command()
@in_command_channel()
async def speak(ctx, *, text: str):
    """使用預設 TTS 語音朗讀輸入的文字"""
    user_id = str(ctx.author.id)
    voice_type = user_voice_settings.get(user_id, "正常")
    model_identifier = voice_map[voice_type]
    try:
        with torch.serialization.safe_globals([RAdam, defaultdict, dict]):
            if model_identifier in tts_instances:
                tts = tts_instances[model_identifier]
            else:
                tts = TTS(model_name=model_identifier, progress_bar=False)
                tts_instances[model_identifier] = tts
        output_file = os.path.join(BASE_DIR, f"voice_{user_id}.wav")
        tts.tts_to_file(text=text, file_path=output_file)
        await ctx.send(f"🔰 **說話方式**：{voice_type}\n💦 **內容**：{text}")
        await ctx.send(file=discord.File(output_file))
        os.remove(output_file)
    except Exception as e:
        await ctx.send(f"❌ 我說不出來：{e}")

@bot.command()
@in_command_channel()
async def transpeak(ctx, source_lang: str, target_lang: str, *, text: str):
    """翻譯文字並使用 TTS 朗讀（同時修剪尾部靜音）"""
    source_lang = source_lang.lower()
    target_lang = target_lang.lower()
    try:
        installed_languages = translate.get_installed_languages()
        source_language = None
        target_language = None
        en_language = None
        for lang in installed_languages:
            if lang.code == source_lang:
                source_language = lang
            if lang.code == target_lang:
                target_language = lang
            if lang.code == "en":
                en_language = lang
        if source_language is None or target_language is None:
            await ctx.send("❌ 未安裝指定語言包，請先安裝相應的離線翻譯包。")
            return
        try:
            translation = source_language.get_translation(target_language)
            translated_text = translation.translate(text)
        except Exception as direct_err:
            if source_lang != "en" and target_lang != "en":
                if en_language is None:
                    await ctx.send("❌ 無法取得英語語言包，無法執行兩段式翻譯。")
                    return
                translation1 = source_language.get_translation(en_language)
                intermediate_text = translation1.translate(text)
                translation2 = en_language.get_translation(target_language)
                translated_text = translation2.translate(intermediate_text)
            else:
                raise direct_err
    except Exception as e:
        await ctx.send(f"❌ 翻譯失敗：{e}")
        return

    if target_lang == "en":
        tts_model = "tts_models/en/ljspeech/glow-tts"
    elif target_lang == "zh":
        tts_model = "tts_models/zh-CN/baker/tacotron2-DDC-GST"
    elif target_lang == "fr":
        tts_model = "tts_models/fr/css10/vits"
    elif target_lang == "es":
        tts_model = "tts_models/es/mai/tacotron2-DDC"
    else:
        tts_model = "tts_models/en/ljspeech/glow-tts"

    try:
        with torch.serialization.safe_globals([RAdam, defaultdict, dict]):
            if tts_model in tts_instances:
                tts = tts_instances[tts_model]
            else:
                tts = TTS(model_name=tts_model, progress_bar=False)
                tts_instances[tts_model] = tts
        output_file = os.path.join(BASE_DIR, f"voice_{ctx.author.id}_trans.wav")
        tts.tts_to_file(text=translated_text, file_path=output_file)
        # 修剪尾部靜音：若最後一段靜音超過 1 秒則修剪
        audio = AudioSegment.from_file(output_file)
        silences = detect_silence(audio, min_silence_len=500, silence_thresh=-50)
        if silences and silences[-1][1] == len(audio) and (audio.duration_seconds - silences[-1][0] / 1000) > 1:
            trimmed = audio[:silences[-1][0]]
            trimmed.export(output_file, format="wav")
        await ctx.send(f"🔰 **翻譯結果**：{translated_text}")
        await ctx.send(file=discord.File(output_file))
        os.remove(output_file)
    except Exception as e:
        await ctx.send(f"❌ 語音生成失敗：{e}")

# -------------------- 音樂播放功能 --------------------
def clean_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

async def download_song(url: str, download_path: str):
    """單純下載 YouTube 音樂，不顯示進度（用於 !play 與 !queue 命令）"""
    loop = asyncio.get_event_loop()
    def run_download():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            clean_file_name = clean_filename(file_name)
            target = os.path.join(BASE_DIR, os.path.basename(clean_file_name))
            if os.path.exists(target):
                os.remove(target)
            shutil.move(file_name, target)
            return target
    audio_file = await loop.run_in_executor(None, run_download)
    return audio_file

async def download_song_with_progress(url: str, progress_message: discord.Message):
    """
    下載 YouTube 音樂並在 Discord 更新下載進度
    """
    loop = asyncio.get_event_loop()
    progress_data = {"last": None}
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                if progress_data["last"] is None or abs(percent - progress_data["last"]) > 5:
                    progress_data["last"] = percent
                    loop.call_soon_threadsafe(asyncio.create_task, progress_message.edit(content=f"📥 正在下載：{percent:.1f}%"))
    def run_download():
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'progress_hooks': [progress_hook],
        }
        # 若存在 cookies.txt 則加入
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            clean_file_name = clean_filename(file_name)
            target = os.path.join(BASE_DIR, os.path.basename(clean_file_name))
            if os.path.exists(target):
                os.remove(target)
            shutil.move(file_name, target)
            return target
    audio_file = await loop.run_in_executor(None, run_download)
    await progress_message.edit(content="📥 下載完成！")
    return audio_file

async def update_control_panel(channel, guild_id, voice_client, now_playing=None):
    """刪除舊的控制面板並發送一個新的，並 pin 置頂"""
    if guild_id in control_messages:
        try:
            await control_messages[guild_id].delete()
        except Exception:
            pass
    content = f"🎛 控制面板\n⏸ 暫停 | ▶️ 播放 | ⏭ 跳過 | ⏪ 減速 | ⏩ 加速\n當前速度：{default_speed.get(guild_id, 1.0):.1f}x"
    if now_playing:
        content += f"\n正在播放：{now_playing}"
    msg = await channel.send(content)
    try:
        await msg.pin()
    except Exception:
        pass
    control_messages[guild_id] = msg
    for emoji in ["⏸", "▶️", "⏭", "⏪", "⏩"]:
        await msg.add_reaction(emoji)

async def track_play_reply(guild_id, message):
    """記錄 !play 指令的回覆訊息，僅保留最新 3 則"""
    play_replies[guild_id].append(message)
    if len(play_replies[guild_id]) > 3:
        old_msg = play_replies[guild_id].pop(0)
        try:
            await old_msg.delete()
        except Exception:
            pass

async def replay_current_track(ctx, voice_client, guild_id):
    """依照最新 default_speed 重新播放目前曲目（從頭開始）"""
    if guild_id in current_track_info:
        audio_file, url = current_track_info[guild_id]
        new_speed = default_speed.get(guild_id, 1.0)
        ffmpeg_options = f'-vn -filter:a "atempo={new_speed}"' if new_speed != 1.0 else '-vn'
        voice_client.stop()
        async def after_playing(error):
            await asyncio.sleep(1)
            if os.path.exists(audio_file):
                os.remove(audio_file)
            await play_next(ctx, voice_client, guild_id)
        voice_client.play(discord.FFmpegPCMAudio(audio_file, options=ffmpeg_options), after=lambda e: bot.loop.create_task(after_playing(e)))
        await update_control_panel(ctx.channel, guild_id, voice_client, now_playing=url)
        msg = await ctx.send(f"🎶 重播：{url}，新速度：{new_speed}x")
        await track_play_reply(guild_id, msg)

async def play_next(ctx, voice_client, guild_id):
    if music_queues[guild_id]:
        audio_file, speed, url = music_queues[guild_id].pop(0)
        # 記錄目前播放的曲目資訊
        current_track_info[guild_id] = (audio_file, url)
        ffmpeg_options = f'-vn -filter:a "atempo={speed}"' if speed != 1.0 else '-vn'
        async def after_playing(error):
            await asyncio.sleep(1)  # 延遲 1 秒再刪除檔案
            if os.path.exists(audio_file):
                os.remove(audio_file)
            await play_next(ctx, voice_client, guild_id)
        voice_client.play(discord.FFmpegPCMAudio(audio_file, options=ffmpeg_options), after=lambda e: bot.loop.create_task(after_playing(e)))
        await update_control_panel(ctx.channel, guild_id, voice_client, now_playing=url)
        play_msg = await ctx.send(f"🎶 正在播放：{url}，速度：{speed}x")
        await track_play_reply(guild_id, play_msg)
    else:
        async def disconnect_later():
            await asyncio.sleep(5)
            if not voice_client.is_playing() and not voice_client.is_paused():
                await voice_client.disconnect()
                if guild_id in control_messages:
                    try:
                        await control_messages[guild_id].delete()
                    except Exception:
                        pass
                    del control_messages[guild_id]
        bot.loop.create_task(disconnect_later())

@bot.command()
@in_command_channel()
async def play(ctx, url: str, speed: float = 1.0):
    """
    撥放 YouTube 音樂連結，可選擇調整播放速度 (建議範圍 0.5~2.0)
    若不在語音頻道，將自動連接使用者所在頻道。
    """
    guild_id = ctx.guild.id
    default_speed[guild_id] = speed
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ 你必須加入語音頻道才能播放音樂！")
        return
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice_client = await ctx.author.voice.channel.connect()
    download_path = os.path.join(BASE_DIR, f"{int(time.time())}.mp3")
    try:
        await ctx.send("🔄 正在下載音樂，請稍等...")
        audio_file = await download_song(url, download_path)
        if not os.path.exists(audio_file):
            await ctx.send("❌ 下載的文件不存在！")
            return
        music_queues[guild_id].append((audio_file, default_speed.get(guild_id, 1.0), url))
        reply = await ctx.send(f"🎶 已加入播放隊列：{url}，速度：{default_speed.get(guild_id, 1.0)}x")
        await track_play_reply(guild_id, reply)
    except Exception as e:
        await ctx.send(f"❌ 下載失敗：{e}")
        if os.path.exists(download_path):
            os.remove(download_path)
        return
    if not voice_client.is_playing():
        await play_next(ctx, voice_client, guild_id)

@bot.command()
@in_command_channel()
async def queue(ctx, *urls: str):
    """批量添加音樂到播放隊列 (預設播放速度由全域變數 default_speed 控制)"""
    if not urls:
        await ctx.send("❌ 請提供音樂鏈接！")
        return
    guild_id = ctx.guild.id
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ 你必須加入語音頻道才能播放音樂！")
        return
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice_client = await ctx.author.voice.channel.connect()
    for url in urls:
        download_path = os.path.join(BASE_DIR, f"{int(time.time())}.mp3")
        try:
            await ctx.send(f"🔄 正在下載音樂：{url}")
            audio_file = await download_song(url, download_path)
            if not os.path.exists(audio_file):
                await ctx.send(f"❌ 下載的文件不存在：{url}")
                continue
            music_queues[guild_id].append((audio_file, default_speed.get(guild_id, 1.0), url))
            reply = await ctx.send(f"🎶 已加入播放隊列：{url}")
            await track_play_reply(guild_id, reply)
        except Exception as e:
            await ctx.send(f"❌ 下載失敗：{e}")
            if os.path.exists(download_path):
                os.remove(download_path)
    if not voice_client.is_playing():
        await play_next(ctx, voice_client, guild_id)

@bot.command()
@in_command_channel()
async def playlist(ctx, url: str, speed: float = 1.0):
    """
    下載並播放播放清單：
    先下載第一首立即撥放，下載進度會在 Discord 中顯示，
    之後依序下載並加入隊列（播放速度預設由參數設定，可用反應表情調整）。
    """
    guild_id = ctx.guild.id
    default_speed[guild_id] = speed
    await ctx.send("🔄 正在獲取播放清單資訊...")
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if 'entries' not in info or len(info['entries']) == 0:
            await ctx.send("❌ 播放清單沒有任何曲目。")
            return
        entries = info['entries']
    except Exception as e:
        await ctx.send(f"❌ 無法獲取播放清單資訊：{e}")
        return
    await ctx.send(f"🎶 找到 {len(entries)} 首曲目。")
    async def process_playlist():
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ 你必須加入語音頻道才能播放音樂！")
            return
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if not voice_client:
            voice_client = await ctx.author.voice.channel.connect()
        for i, entry in enumerate(entries):
            if entry is None:
                continue
            track_url = entry.get("url")
            if not track_url.startswith("http"):
                track_url = f"https://www.youtube.com/watch?v={track_url}"
            progress_msg = await ctx.send(f"📥 正在下載第 {i+1} 首曲目：{track_url}\n進度：0%")
            try:
                audio_file = await download_song_with_progress(track_url, progress_msg)
            except Exception as e:
                await ctx.send(f"❌ 下載第 {i+1} 首失敗：{e}")
                continue
            music_queues[guild_id].append((audio_file, default_speed.get(guild_id, 1.0), track_url))
            reply = await ctx.send(f"🎶 已加入播放隊列：{track_url}")
            await track_play_reply(guild_id, reply)
            if not voice_client.is_playing():
                await play_next(ctx, voice_client, guild_id)
        await ctx.send("✅ 播放清單全部處理完成！")
    bot.loop.create_task(process_playlist())

@bot.command()
@in_command_channel()
async def search(ctx, *, query: str):
    """
    搜索 YouTube 並顯示前 30 個結果，
    請回覆數字選擇要播放的曲目（1-30），超時 60 秒則取消。
    """
    try:
        ydl_opts = {
            'default_search': 'ytsearch30',
            'quiet': True,
            'noplaylist': True,
            'ignoreerrors': True,
        }
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            entries = [entry for entry in info['entries'] if entry is not None]
            if not entries:
                await ctx.send("❌ 未找到有效結果。")
                return
            result_list = ""
            for i, video in enumerate(entries, start=1):
                title = video.get('title', 'No Title')
                duration = video.get('duration', 0)
                m, s = divmod(duration, 60)
                duration_str = f"{m:02d}:{s:02d}"
                result_list += f"{i}. {title} ({duration_str})\n"
            await ctx.send("搜索結果如下：\n" + result_list + "\n請輸入數字選擇要播放的曲目 (1-" + str(len(entries)) + ")，回覆超過 60 秒則取消。")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            try:
                reply = await bot.wait_for("message", check=check, timeout=60)
                choice = int(reply.content)
                if 1 <= choice <= len(entries):
                    selected_video = entries[choice - 1]
                    url = selected_video.get('webpage_url')
                    await ctx.send(f"你選擇了：{selected_video.get('title')}\n正在播放...")
                    await ctx.invoke(play, url=url)
                else:
                    await ctx.send("數字不在範圍內，取消選擇。")
            except asyncio.TimeoutError:
                await ctx.send("超時未回覆，取消選擇。")
        else:
            await ctx.send("❌ 未找到結果。")
    except Exception as e:
        await ctx.send(f"❌ 搜索失敗：{e}")

@bot.command()
@in_command_channel()
async def stop(ctx):
    """停止播放音樂並清除播放隊列"""
    guild_id = ctx.guild.id
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        music_queues[guild_id].clear()
        await ctx.send("⏹ 停止播放音樂並清除隊列。")
    else:
        await ctx.send("❌ 沒有音樂在播放。")

@bot.command()
@in_command_channel()
async def pause(ctx):
    """暫停播放音樂"""
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸ 暫停音樂播放。")
    else:
        await ctx.send("❌ 沒有音樂在播放。")

@bot.command()
@in_command_channel()
async def resume(ctx):
    """恢復播放音樂"""
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ 恢復播放音樂。")
    else:
        await ctx.send("❌ 音樂未暫停。")

@bot.command()
@in_command_channel()
async def leave(ctx):
    """讓機器人離開語音頻道並清除播放隊列"""
    guild_id = ctx.guild.id
    music_queues[guild_id].clear()
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("🚶‍♂️ 我已經離開語音頻道並清除隊列。")
    else:
        await ctx.send("❌ 我不在語音頻道。")

# -------------------- 反應表情控制 --------------------
@bot.event
async def on_raw_reaction_add(payload):
    # 取消訂選功能：若反應發生在訂選頻道，直接忽略
    if payload.channel_id == REACTION_ROLE_CHANNEL_ID:
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    if payload.user_id == bot.user.id:
        return
    if guild.id not in control_messages:
        return
    control_msg = control_messages[guild.id]
    if payload.message_id != control_msg.id:
        return
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return
    voice_client = discord.utils.get(bot.voice_clients, guild=guild)
    if not voice_client:
        return
    emoji = str(payload.emoji)
    if emoji == "⏸":
        if voice_client.is_playing():
            voice_client.pause()
            await channel.send("⏸ 已暫停播放。")
    elif emoji == "▶️":
        if voice_client.is_paused():
            voice_client.resume()
            await channel.send("▶️ 已恢復播放。")
    elif emoji == "⏭":
        voice_client.stop()
        await channel.send("⏭ 已跳過當前曲目。")
    elif emoji == "⏩":
        current_speed = default_speed.get(guild.id, 1.0)
        new_speed = current_speed + 0.1
        default_speed[guild.id] = new_speed
        await channel.send(f"⏩ 加速，當前速度：{new_speed:.1f}x")
        await replay_current_track(channel, voice_client, guild.id)
    elif emoji == "⏪":
        current_speed = default_speed.get(guild.id, 1.0)
        new_speed = max(0.5, current_speed - 0.1)
        default_speed[guild.id] = new_speed
        await channel.send(f"⏪ 減速，當前速度：{new_speed:.1f}x")
        await replay_current_track(channel, voice_client, guild.id)
    try:
        member = await guild.fetch_member(payload.user_id)
        await control_msg.remove_reaction(payload.emoji, member)
    except Exception:
        pass
    await update_control_panel(channel, guild.id, voice_client)

# -------------------- 事件處理與啟動 --------------------
@bot.event
async def on_member_join(member):
    """新成員加入歡迎訊息"""
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        try:
            embed = discord.Embed(
                title="🎊 歡迎新朋友！",
                description=f"{member.mention} 加入了我們的伺服器！\n\n"
                            f"• 請先閱讀 <#{COMMAND_CHANNEL_ID}> 的規則\n"
                            f"• 前往 <#{REACTION_ROLE_CHANNEL_ID}> 選擇身分組",
                color=0xFFD700
            )
            embed.set_thumbnail(url=member.avatar.url)
            await welcome_channel.send(embed=embed)
        except Exception as e:
            print(f"發送歡迎訊息失敗：{e}")

@bot.event
async def on_ready():
    """機器人啟動完成事件"""
    print(f"\n{'='*40}")
    print(f'登入身份：{bot.user.name} ({bot.user.id})')
    print(f'指令頻道：{COMMAND_CHANNEL_ID}')
    print(f'已加載 {len(user_voice_settings)} 個用戶語音設定')
    print(f'已註冊指令：{len(bot.commands)} 個')
    print(f'就緒時間：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    print(f"{'='*40}\n")
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="!help 查看指令"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    """全局指令錯誤處理"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ 未知指令，輸入 `!help` 查看可用指令")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 缺少必要參數：`{error.param.name}`")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        await ctx.send(f"⚠️ 發生未處理錯誤：```{str(error)}```")
        raise error

# -------------------- 啟動機器人 --------------------
if __name__ == "__main__":
    print("正在初始化機器人...")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token 無效或登入失敗")
    except KeyboardInterrupt:
        print("\n正在安全關閉機器人...")
        async def disconnect_voice_clients():
            for vc in bot.voice_clients:
                await vc.disconnect()
            print("已斷開所有語音連接")
        import asyncio
        asyncio.run(disconnect_voice_clients())
    finally:
        print("機器人進程已終止")
