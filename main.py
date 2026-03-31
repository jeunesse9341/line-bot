import base64
import requests
from openai import OpenAI
from fastapi import FastAPI, Request

client = OpenAI()
app = FastAPI()

LINE_TOKEN = "ここはそのまま"


# 🔥 AI認識関数
def recognize_product(image_path):
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
この画像の商品を転売目的で特定してください。

【出力】
・商品名
・メーカー
・型番
・カテゴリ
・メルカリ検索キーワード（3つ）
・確信度（%）
"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content


# 🔥 webhook
@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()

    for event in body["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]

            # 画像チェック
            if event["message"]["type"] == "image":

                message_id = event["message"]["id"]

                headers = {
                    "Authorization": f"Bearer {LINE_TOKEN}"
                }

                image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
                response = requests.get(image_url, headers=headers)

                with open("image.jpg", "wb") as f:
                    f.write(response.content)

                result = recognize_product("image.jpg")

                send_line(reply_token, result)

            else:
                send_line(reply_token, "画像送ってね📸")

    return {"status": "ok"}


# 🔥 LINE返信
def send_line(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }

    requests.post(url, headers=headers, json=data)
