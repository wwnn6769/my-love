from flask import Flask, redirect, url_for, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# 導入 NLP、日誌的 Blueprint
from src.nlp.basic_translator import translator_bp
from src.nlp.text_to_speech import tts_bp
from src.nlp.transpeak import transpeak_bp
from src.data_logging.logging_module import logging_bp

app = Flask(__name__)
app.secret_key = 'your_random_secure_key'  # 請替換為安全的隨機字串

# 設定 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 簡單用戶模型與模擬資料庫
class User(UserMixin):
    def __init__(self, id):
        self.id = id

users = {
    'testuser': {'password': 'testpass'}
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = users.get(username)
        if user_data and password == user_data['password']:
            user = User(username)
            login_user(user)
            return "登入成功！<br><a href='/'>返回首頁</a>"
        else:
            return "用戶名或密碼錯誤。"
    return '''
    <form action="" method="post">
        <input type="text" name="username" placeholder="用戶名" required>
        <input type="password" name="password" placeholder="密碼" required>
        <input type="submit" value="登入">
    </form>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return "已登出。<br><a href='/login'>重新登入</a>"

@app.route('/')
def index():
    if current_user.is_authenticated:
        return (
            "歡迎 {}！<br>"
            "<a href='/basic_translate_test'>測試翻譯</a><br>"
            "<a href='/text_to_speech_test'>測試語音生成</a><br>"
            "<a href='/transpeak_test'>測試 Transpeak</a><br>"
            "<a href='/log_task_test'>測試日誌更新</a><br>"
            "<a href='/edit_video_test'>測試影片剪輯</a><br>"
            "<a href='/welcome'>新人引導</a><br>"
            "<a href='/logout'>登出</a>"
        ).format(current_user.id)
    return "請先<a href='/login'>登入</a>。"

# 以下為測試頁面（用於調試各功能，實際部署時可移除）
@app.route('/basic_translate_test', methods=['GET'])
@login_required
def basic_translate_test():
    return '''
    <h3>離線翻譯測試</h3>
    <form id="translateForm">
        <textarea name="text" rows="4" cols="50" placeholder="例如：你好 世界"></textarea><br>
        <button type="button" onclick="submitForm()">翻譯</button>
    </form>
    <div id="result"></div>
    <script>
    function submitForm() {
        const text = document.querySelector('#translateForm textarea').value;
        fetch('/basic_translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('result').innerText = "翻譯結果：" + data.translation;
        })
        .catch(error => { console.error('Error:', error); });
    }
    </script>
    '''

@app.route('/text_to_speech_test', methods=['GET'])
@login_required
def text_to_speech_test():
    return '''
    <h3>語音生成測試</h3>
    <form id="ttsForm">
        <textarea name="text" rows="4" cols="50" placeholder="例如：這是一個測試，請聽見我的聲音。"></textarea><br>
        <button type="button" onclick="submitTTS()">生成語音</button>
    </form>
    <div id="ttsResult"></div>
    <script>
    function submitTTS() {
        const text = document.querySelector('#ttsForm textarea').value;
        fetch('/text_to_speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        })
        .then(response => response.blob())
        .then(blob => {
            const audioUrl = URL.createObjectURL(blob);
            document.getElementById('ttsResult').innerHTML = '<audio controls src="' + audioUrl + '"></audio>';
        })
        .catch(error => { console.error('Error:', error); });
    }
    </script>
    '''

@app.route('/transpeak_test', methods=['GET'])
@login_required
def transpeak_test():
    return '''
    <h3>Transpeak 測試 (翻譯後語音)</h3>
    <form id="transpeakForm">
        <textarea name="text" rows="4" cols="50" placeholder="例如：你好"></textarea><br>
        <button type="button" onclick="submitTranspeak()">執行 Transpeak</button>
    </form>
    <div id="transpeakResult"></div>
    <script>
    function submitTranspeak() {
        const text = document.querySelector('#transpeakForm textarea').value;
        fetch('/transpeak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        })
        .then(response => response.blob())
        .then(blob => {
            const audioUrl = URL.createObjectURL(blob);
            document.getElementById('transpeakResult').innerHTML = '<audio controls src="' + audioUrl + '"></audio>';
        })
        .catch(error => { console.error('Error:', error); });
    }
    </script>
    '''

@app.route('/log_task_test', methods=['GET'])
@login_required
def log_task_test():
    return '''
    <h3>日誌更新測試</h3>
    <form id="logForm">
        <textarea name="task_description" rows="3" cols="50" placeholder="任務描述"></textarea><br>
        <textarea name="paths" rows="2" cols="50" placeholder="相關路徑(用逗號分隔)"></textarea><br>
        <textarea name="thoughts" rows="3" cols="50" placeholder="思考過程"></textarea><br>
        <textarea name="training_data" rows="5" cols="50" placeholder="訓練資料內容"></textarea><br>
        <button type="button" onclick="submitLog()">更新日誌</button>
    </form>
    <div id="logResult"></div>
    <script>
    function submitLog() {
        const task_description = document.querySelector('textarea[name="task_description"]').value;
        const paths = document.querySelector('textarea[name="paths"]').value.split(',');
        const thoughts = document.querySelector('textarea[name="thoughts"]').value;
        const training_data = document.querySelector('textarea[name="training_data"]').value;
        fetch('/log_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_description: task_description,
                paths: paths,
                thoughts: thoughts,
                training_data: training_data
            })
        })
        .then(response => response.json())
        .then(data => { document.getElementById('logResult').innerText = data.message; })
        .catch(error => { console.error('Error:', error); });
    }
    </script>
    '''

@app.route('/edit_video_test', methods=['GET', 'POST'])
@login_required
def edit_video_test():
    if request.method == 'POST':
        data = request.get_json(force=True)
        input_video = data.get('input_video')
        output_video = data.get('output_video')
        start_time = data.get('start_time', 0)
        end_time = data.get('end_time', 10)
        
        from src.video.edit_video import clip_video
        result, process_info = clip_video(input_video, output_video, start_time, end_time)
        if result:
            return jsonify({"message": "影片剪輯完成", "process": process_info, "output": output_video})
        else:
            return jsonify({"error": "影片剪輯失敗"}), 500
    else:
        return '''
        <h3>影片剪輯測試</h3>
        <p>請使用 JSON 格式的 POST 請求來測試影片剪輯功能。參數：</p>
        <ul>
            <li><strong>input_video</strong>：原始影片完整路徑</li>
            <li><strong>output_video</strong>：輸出影片完整路徑</li>
            <li><strong>start_time</strong>：開始時間（秒）</li>
            <li><strong>end_time</strong>：結束時間（秒）</li>
        </ul>
        '''

# 新人引導頁面（例如歡迎信息）
@app.route('/welcome', methods=['GET'])
@login_required
def welcome():
    return "歡迎新人！請仔細閱讀頻道公告以瞭解使用方式。"

if __name__ == '__main__':
    # 註冊所有 Blueprint
    app.register_blueprint(translator_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(transpeak_bp)
    app.register_blueprint(logging_bp)
    app.run(host='0.0.0.0', port=5000, debug=True)
