from flask import Blueprint, request, send_file, jsonify
from gtts import gTTS
from io import BytesIO

tts_bp = Blueprint('tts_bp', __name__)

def generate_speech(text: str, lang: str = 'en', output_file: str = "speech.mp3"):
    tts = gTTS(text=text, lang=lang)
    tts.save(output_file)

@tts_bp.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "未提供文字"}), 400
    try:
        tts = gTTS(text=text, lang='en')
        audio_io = BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        return send_file(audio_io, mimetype="audio/mpeg", as_attachment=False, download_name="speech.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(tts_bp)
    app.run(debug=True)
