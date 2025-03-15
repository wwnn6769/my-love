# utils/config.py
import os
from dotenv import load_dotenv

# 請將 Token 放在環境變數中，或暫時自行填入（開發時使用）
load_dotenv()
TOKEN = os.getenv("TOKEN", "").strip()


# 頻道 ID
COMMAND_CHANNEL_ID = 1345084711302729839   # 指令使用頻道
WELCOME_CHANNEL_ID = 1345063015203995700    # 歡迎新成員的頻道
REACTION_ROLE_CHANNEL_ID = 1345086945876905994  # 反應角色（訂選）頻道

# 音樂下載存放資料夾，請根據自己的環境調整路徑
BASE_DIR = r"D:\Assistant\dc music"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
