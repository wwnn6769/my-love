from flask import Blueprint, request, jsonify
from googletrans import Translator

translator_bp = Blueprint('translator_bp', __name__)
translator = Translator()

def translate_text(text: str, dest: str = 'en') -> str:
    result = translator.translate(text, dest=dest)
    return result.text

@translator_bp.route('/basic_translate', methods=['POST'])
def basic_translate():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "未提供文字"}), 400
    try:
        translated = translate_text(text, dest='en')
        return jsonify({"translation": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(translator_bp)
    app.run(debug=True)
