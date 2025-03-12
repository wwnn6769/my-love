# src/chat_model.py

import requests

def get_chat_response(user_message):
    """
    这里调用你的 ChatGPT 免费推理接口，
    目前示例使用伪代码，实际请参考具体API文档
    """
    # 伪代码示例：构造请求数据
    api_url = "https://api.example.com/chat"  # 替换为实际接口
    payload = {"prompt": user_message}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        result = response.json()
        return result.get("response", "抱歉，我没能理解你的意思。")
    else:
        return "对不起，服务出现问题。"

if __name__ == "__main__":
    while True:
        message = input("你说：")
        reply = get_chat_response(message)
        print("机器人：", reply)
