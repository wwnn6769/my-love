from flask import Blueprint, request, jsonify

# 建立一個 Blueprint，用於離線翻譯模組
translator_bp = Blueprint('translator_bp', __name__)

# 預定義一個簡單的字典映射（僅示範用途）
translation_dict = {
    "你好": "Hello",
    "世界": "World",
    "我": "I",
    "愛": "love",
    "你": "you",
    "早安": "Good morning",
    "晚安": "Good night",
    "學習": "study",
    "人工智慧": "Artificial Intelligence",
    "測試": "test"
}

def simple_translate(text):
    # 將輸入文字以空格分隔，逐詞翻譯
    words = text.split()  # 注意：中文通常不以空格分詞，此處僅為示範
    translated_words = [translation_dict.get(word, word) for word in words]
    return ' '.join(translated_words)

@translator_bp.route('/basic_translate', methods=['POST'])
def translate_endpoint():
    # 強制解析 JSON，忽略 Content-Type 標頭（確保能讀取數據）
    data = request.get_json(force=True)
    if not data or 'text' not in data:
        return jsonify({"error": "請提供要翻譯的文字"}), 400
    input_text = data['text']
    output_text = simple_translate(input_text)
    return jsonify({"translation": output_text})
