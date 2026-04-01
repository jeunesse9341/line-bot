import base64
import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from fastapi import FastAPI, Request

# 🔥 設定
LINE_TOKEN = "SJf2O2LASoEHeetmLRbxF/8miebqmnuNHD8y7PHV5zqDykovIDJQ/IyxzhgasdthCMgwpZq3ZQUVVd7rXW/kvJg6C6rBH4uYNGQsGsC7jbS4cE4N5MKmS0Mdu7VXfZ1yfjqqlox22hNuGlU2+JVchwdB04t89/1O/w1cDnyilFU="
client = OpenAI()

app = FastAPI()


# 🔥 メルカリ価格取得
def get_mercari_prices(keyword):
    url = f"https://www.mercari.com/jp/search/?keyword={keyword}&status=sold_out"
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    prices = []

    for span in soup.find_all("span"):
        text = span.get_text()
        if "¥" in text:
            price = re.sub(r"[¥,]", "", text)
            if price.isdigit():
                prices.append(int(price))

    return prices[:10]


# 🔥 キーワード抽出
def extract_keyword(ai_result):
    lines = ai_result.split("\n")
    for line in lines:
        if "商品名" in line:
            return line.replace("・商品名", "").replace("商品名", "").replace("：", "").strip()
    return ai_result[:20]


# 🔥 AIで商品認識
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
この画像に写っている商品を必ず推測してください。

完全に一致しなくてもいいので、
見た目・ロゴ・形状から最も近い商品名を出してください。

【出力】
・商品名
・メーカー
・型番（推測でもOK）
・カテゴリ
・メルカリ検索キーワード（3つ）
・確信度（%）

※絶対に「分からない」とは言わず、必ず候補を出す
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


# 🔥 webhook
@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()

    for event in body["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]

            if event["message"]["type"] == "text":
                send_line(reply_token, "画像送ってね📸")
                return {"status": "ok"}

            if event["message"]["type"] == "image":
                message_id = event["message"]["id"]

                headers = {
                    "Authorization": f"Bearer {LINE_TOKEN}"
                }

                image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
                response = requests.get(image_url, headers=headers)

                with open("image.jpg", "wb") as f:
                    f.write(response.content)

                try:
                    result = recognize_product("image.jpg")

                    keyword = extract_keyword(result)
                    prices = get_mercari_prices(keyword)

                    if prices:
                        avg_price = sum(prices) // len(prices)
                        price_text = f"\n平均販売価格：約{avg_price}円"
                    else:
                        price_text = "\n価格取得できませんでした"

                    final_text = result + price_text

                except Exception as e:
                    final_text = f"エラー: {str(e)}"

                send_line(reply_token, final_text)

    return {"status": "ok"}
