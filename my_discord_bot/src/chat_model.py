# src/chat_model.py

import requests

def get_chat_response(user_message):
    """
    调用 ChatGPT 免费推理接口生成回复
    请将 api_url 替换为你实际使用的推理接口地址，
    并根据接口文档调整请求格式和参数。
    """
    api_url = "https://api.yourfreechatgpt.com/generate"  # 示例接口地址
    payload = {"prompt": user_message}
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "我暂时不知道该怎么回答。")
        else:
            return "服务暂时不可用，请稍后再试。"
    except Exception as e:
        return f"请求出错：{e}"

if __name__ == "__main__":
    while True:
        msg = input("你说：")
        print("机器人：", get_chat_response(msg))
