import base64
from openai import OpenAI

client = OpenAI()def recognize_product(image_path):
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

【条件】
・検索でヒットする正確な名称
・曖昧なら候補3つ
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

    return response.choices[0].message.contentfrom fastapi import FastAPI, Request
import requests

app = FastAPI()

LINE_TOKEN = "SJf2O2LASoEHeetmLRbxF/8miebqmnuNHD8y7PHV5zqDykovIDJQ/IyxzhgasdthCMgwpZq3ZQUVVd7rXW/kvJg6C6rBH4uYNGQsGsC7jbS4cE4N5MKmS0Mdu7VXfZ1yfjqqlox22hNuGlU2+JVchwdB04t89/1O/w1cDnyilFU="

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()

    for event in body["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]

            @app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()

    for event in body["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]

            # 画像かどうかチェック
            if event["message"]["type"] == "image":

                message_id = event["message"]["id"]

                # 画像取得
                headers = {
                    "Authorization": f"Bearer {LINE_TOKEN}"
                }
                image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"

                import requests
                response = requests.get(image_url, headers=headers)

                # 画像保存
                with open("image.jpg", "wb") as f:
                    f.write(response.content)

                # AI認識
                result = recognize_product("image.jpg")

                # LINE返信
                send_line(reply_token, result)

            else:
                send_line(reply_token, "画像送ってね📸")

    return {"status": "ok"}

    return {"status": "ok"}


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
