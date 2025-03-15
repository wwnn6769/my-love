from flask import Blueprint, request, send_file, jsonify
from googletrans import Translator
from gtts import gTTS
from io import BytesIO

transpeak_bp = Blueprint('transpeak_bp', __name__)

def transpeak_text(text: str, target_lang: str = 'en', tts_lang: str = 'en', output_file: str = "transpeak.mp3"):
    translator = Translator()
    result = translator.translate(text, dest=target_lang)
    translated_text = result.text
    tts = gTTS(text=translated_text, lang=tts_lang)
    tts.save(output_file)
    return output_file

@transpeak_bp.route('/transpeak', methods=['POST'])
def transpeak():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "未提供文字"}), 400
    try:
        translator = Translator()
        result = translator.translate(text, dest='en')
        translated_text = result.text
        tts = gTTS(text=translated_text, lang='en')
        audio_io = BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        return send_file(audio_io, mimetype="audio/mpeg", as_attachment=False, download_name="transpeak.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(transpeak_bp)
    app.run(debug=True)
