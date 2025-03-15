import os
from flask import Blueprint, request, jsonify
import logging

logging_bp = Blueprint('logging_bp', __name__)

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "task.log")

logger = logging.getLogger("TaskLogger")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

@logging_bp.route('/log_task', methods=['POST'])
def log_task():
    data = request.get_json(force=True)
    task_description = data.get("task_description", "")
    paths = data.get("paths", [])
    thoughts = data.get("thoughts", "")
    training_data = data.get("training_data", "")
    
    if not task_description:
        return jsonify({"error": "任務描述為必填"}), 400

    log_entry = f"Task: {task_description}\nPaths: {paths}\nThoughts: {thoughts}\nTraining Data: {training_data}\n"
    try:
        logger.info(log_entry)
        return jsonify({"message": "日誌更新成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(logging_bp)
    app.run(debug=True)
