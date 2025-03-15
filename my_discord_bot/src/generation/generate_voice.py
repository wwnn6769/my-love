def generate_voice(text: str, output_file: str = "generated_voice.mp3") -> bool:
    """
    基礎生成語音，使用 gTTS 實現。
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_file)
        return True
    except Exception as e:
        print(f"語音生成錯誤：{e}")
        return False

if __name__ == '__main__':
    if generate_voice("This is a test.", "test_voice.mp3"):
        print("語音生成成功")
    else:
        print("語音生成失敗")
