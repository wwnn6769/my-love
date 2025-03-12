# D:\Assistant\src\data_logging\logging_module.py
import os
from flask import Blueprint, request, jsonify
from datetime import datetime

# 建立一個 Blueprint 用於日誌模組
logging_bp = Blueprint('logging_bp', __name__)

# 定義日誌與訓練資料檔案的路徑
LOG_FILE = os.path.join("logs", "task_log.txt")          # 日誌檔 (將在 D:\Assistant\logs 中)
TRAINING_DATA_FILE = os.path.join("logs", "training_data.txt")  # 訓練資料檔

# 確保 logs 資料夾存在
if not os.path.exists("logs"):
    os.makedirs("logs")

@logging_bp.route('/log_task', methods=['POST'])
def log_task():
    """
    API 端點：接受 JSON 格式的 POST 請求，格式必須包含以下欄位：
      - task_description：任務描述
      - paths：相關檔案路徑（選填，陣列格式）
      - thoughts：思考過程描述（選填）
      - training_data：本次任務的訓練資料內容（必填，這是用於儲存新的訓練資料）
    此接口將：
      1. 儲存最新的訓練資料到 TRAINING_DATA_FILE（覆蓋舊內容）
      2. 寫入一條任務日誌到 LOG_FILE（覆蓋模式，可根據需求改為追加模式）
    """
    data = request.get_json(force=True)
    if not data or 'task_description' not in data or 'training_data' not in data:
        return jsonify({"error": "請提供 task_description 和 training_data 欄位"}), 400

    task_description = data['task_description']
    paths = data.get('paths', [])
    thoughts = data.get('thoughts', "無")
    training_data = data['training_data']

    # 生成日誌條目（包括時間、用戶信息與任務細節）
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (f"[{timestamp}] 任務描述: {task_description}\n"
                 f"相關路徑: {paths}\n"
                 f"思考過程: {thoughts}\n\n")

    try:
        # 儲存訓練資料（覆蓋原有檔案）
        with open(TRAINING_DATA_FILE, "w", encoding="utf-8") as f_train:
            f_train.write(training_data)

        # 寫入日誌（覆蓋舊日誌，可改為追加模式：mode="a"）
        with open(LOG_FILE, "w", encoding="utf-8") as f_log:
            f_log.write(log_entry)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "任務日誌與訓練資料更新成功"}), 200

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(logging_bp)
    app.run(debug=True)
