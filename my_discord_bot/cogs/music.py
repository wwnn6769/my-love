# cogs/music.py
import os
import time
import re
import asyncio
import shutil
from collections import defaultdict

import discord
from discord.ext import commands
import yt_dlp
from pydub import AudioSegment
from pydub.silence import detect_silence

from utils.config import COMMAND_CHANNEL_ID, REACTION_ROLE_CHANNEL_ID, BASE_DIR

# 全域變數
music_queues = defaultdict(list)
control_messages = {}
default_speed = {}
play_replies = defaultdict(list)
current_track_info = {}

# yt_dlp 選項設定
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True}
if os.path.exists("cookies.txt"):
    YDL_OPTIONS['cookiefile'] = "cookies.txt"

def clean_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

async def download_song(url: str, download_path: str):
    """單純下載 YouTube 音樂"""
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
    """下載 YouTube 音樂並更新 Discord 中的下載進度"""
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
    """更新控制面板訊息，並 pin 置頂"""
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
    """僅保留最新 3 筆 !play 指令回覆"""
    play_replies[guild_id].append(message)
    if len(play_replies[guild_id]) > 3:
        old_msg = play_replies[guild_id].pop(0)
        try:
            await old_msg.delete()
        except Exception:
            pass

async def replay_current_track(ctx, voice_client, guild_id):
    """根據最新速度重新播放當前曲目"""
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
        voice_client.play(discord.FFmpegPCMAudio(audio_file, options=ffmpeg_options), 
                           after=lambda e: asyncio.create_task(after_playing(e)))
        await update_control_panel(ctx.channel, guild_id, voice_client, now_playing=url)
        msg = await ctx.send(f"🎶 重播：{url}，新速度：{new_speed}x")
        await track_play_reply(guild_id, msg)

async def play_next(ctx, voice_client, guild_id):
    if music_queues[guild_id]:
        audio_file, speed, url = music_queues[guild_id].pop(0)
        current_track_info[guild_id] = (audio_file, url)
        ffmpeg_options = f'-vn -filter:a "atempo={speed}"' if speed != 1.0 else '-vn'
        async def after_playing(error):
            await asyncio.sleep(1)
            if os.path.exists(audio_file):
                os.remove(audio_file)
            await play_next(ctx, voice_client, guild_id)
        voice_client.play(discord.FFmpegPCMAudio(audio_file, options=ffmpeg_options), 
                           after=lambda e: asyncio.create_task(after_playing(e)))
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
        asyncio.create_task(disconnect_later())

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def play(self, ctx, url: str, speed: float = 1.0):
        """
        撥放 YouTube 音樂連結，可選擇調整播放速度 (建議 0.5~2.0)
        若使用者未在語音頻道，則回傳錯誤訊息。
        """
        guild_id = ctx.guild.id
        default_speed[guild_id] = speed
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ 你必須加入語音頻道才能播放音樂！")
            return
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
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

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def queue(self, ctx, *urls: str):
        """批量添加音樂到播放隊列 (預設播放速度由 default_speed 控制)"""
        if not urls:
            await ctx.send("❌ 請提供音樂鏈接！")
            return
        guild_id = ctx.guild.id
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ 你必須加入語音頻道才能播放音樂！")
            return
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
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

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def playlist(self, ctx, url: str, speed: float = 1.0):
        """
        下載並播放播放清單：
        先下載第一首立即撥放，之後依序下載並加入隊列。
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
            voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
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
        asyncio.create_task(process_playlist())

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def search(self, ctx, *, query: str):
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
                    reply = await self.bot.wait_for("message", check=check, timeout=60)
                    choice = int(reply.content)
                    if 1 <= choice <= len(entries):
                        selected_video = entries[choice - 1]
                        url = selected_video.get('webpage_url')
                        await ctx.send(f"你選擇了：{selected_video.get('title')}\n正在播放...")
                        await ctx.invoke(self.play, url=url)
                    else:
                        await ctx.send("數字不在範圍內，取消選擇。")
                except asyncio.TimeoutError:
                    await ctx.send("超時未回覆，取消選擇。")
            else:
                await ctx.send("❌ 未找到結果。")
        except Exception as e:
            await ctx.send(f"❌ 搜索失敗：{e}")

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def stop(self, ctx):
        """停止播放音樂並清除播放隊列"""
        guild_id = ctx.guild.id
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            music_queues[guild_id].clear()
            await ctx.send("⏹ 停止播放音樂並清除隊列。")
        else:
            await ctx.send("❌ 沒有音樂在播放。")

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def pause(self, ctx):
        """暫停播放音樂"""
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸ 暫停音樂播放。")
        else:
            await ctx.send("❌ 沒有音樂在播放。")

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def resume(self, ctx):
        """恢復播放音樂"""
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ 恢復播放音樂。")
        else:
            await ctx.send("❌ 音樂未暫停。")

    @commands.command()
    @commands.check(lambda ctx: ctx.channel.id == COMMAND_CHANNEL_ID)
    async def leave(self, ctx):
        """讓機器人離開語音頻道並清除播放隊列"""
        guild_id = ctx.guild.id
        music_queues[guild_id].clear()
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client:
            await voice_client.disconnect()
            await ctx.send("🚶‍♂️ 我已經離開語音頻道並清除隊列。")
        else:
            await ctx.send("❌ 我不在語音頻道。")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # 若反應發生在訂選頻道則忽略
        if payload.channel_id == REACTION_ROLE_CHANNEL_ID:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if payload.user_id == self.bot.user.id:
            return
        if guild.id not in control_messages:
            return
        control_msg = control_messages[guild.id]
        if payload.message_id != control_msg.id:
            return
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return
        voice_client = discord.utils.get(self.bot.voice_clients, guild=guild)
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

def setup(bot):
    bot.add_cog(MusicCommands(bot))
