# cogs/tts.py
import os
import json
from collections import defaultdict

import discord
from discord.ext import commands

import torch.serialization
from TTS.api import TTS
from TTS.utils.radam import RAdam
from argostranslate import translate
from pydub import AudioSegment
from pydub.silence import detect_silence

from utils.config import COMMAND_CHANNEL_ID, BASE_DIR

# 語音風格對應 TTS 模型
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

# 限制指令只能在指定頻道使用
def in_command_channel():
    async def predicate(ctx):
        if ctx.channel.id != COMMAND_CHANNEL_ID:
            await ctx.send(f"請到 <#{COMMAND_CHANNEL_ID}> 使用指令！")
            return False
        return True
    return commands.check(predicate)

class TTSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @in_command_channel()
    async def setvoice(self, ctx, voice_type: str):
        """設定使用者 TTS 語音風格"""
        user_id = str(ctx.author.id)
        if voice_type not in voice_map:
            await ctx.send(f"⚠️ 無效的語音風格 `{voice_type}`，我目前支援：{', '.join(voice_map.keys())}")
            return
        user_voice_settings[user_id] = voice_type
        save_voice_settings(user_voice_settings)
        await ctx.send(f"✅ **已設定你的語音風格為 `{voice_type}`**")

    @commands.command()
    @in_command_channel()
    async def speak(self, ctx, *, text: str):
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

    @commands.command()
    @in_command_channel()
    async def transpeak(self, ctx, source_lang: str, target_lang: str, *, text: str):
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

def setup(bot):
    bot.add_cog(TTSCommands(bot))
