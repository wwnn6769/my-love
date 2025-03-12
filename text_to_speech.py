# D:\Assistant\src\nlp\text_to_speech.py
import pyttsx3
import tempfile
import os
from flask import Blueprint, request, send_file, jsonify

# 建立一個 Blueprint 用於語音生成模組
tts_bp = Blueprint('tts_bp', __name__)

# 初始化 pyttsx3 語音引擎
engine = pyttsx3.init()
# 設定預設語速與音量（根據需求可調整）
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

@tts_bp.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """
    API 端點：接受 JSON 格式的 POST 請求，格式必須包含 "text" 欄位，
    並將文字轉換成語音，返回一個音訊檔（.wav 格式）。
    """
    data = request.get_json(force=True)
    if not data or 'text' not in data:
        return jsonify({"error": "請提供要轉換的文字"}), 400

    input_text = data['text']
    
    # 使用 temporary file 存放生成的語音檔
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_filename = temp_audio.name

    # 利用 pyttsx3 將文字轉成語音並存入檔案中
    engine.save_to_file(input_text, temp_filename)
    engine.runAndWait()

    # 回傳生成的音訊檔案
    return send_file(temp_filename, mimetype='audio/wav')

if __name__ == '__main__':
    # 測試此模組：請先建立虛擬環境並在該模組目錄下執行
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(tts_bp)
    app.run(debug=True)
