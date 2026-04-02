import base64
import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from fastapi import FastAPI, Request

LINE_TOKEN = "SJf2O2LASoEHeetmLRbxF/8miebqmnuNHD8y7PHV5zqDykovIDJQ/IyxzhgasdthCMgwpZq3ZQUVVd7rXW/kvJg6C6rBH4uYNGQsGsC7jbS4cE4N5MKmS0Mdu7VXfZ1yfjqqlox22hNuGlU2+JVchwdB04t89/1O/w1cDnyilFU="
client = OpenAI()

app = FastAPI()


# 🔥 メルカリ価格取得（取れたらラッキー）
def get_mercari_prices(keyword):
    url = f"https://www.mercari.com/jp/search/?keyword={keyword}&status=sold_out"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ja-JP"
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


# 🔥 AI結果からキーワード抽出
def extract_keywords(ai_result):
    for line in ai_result.split("\n"):
        if "メルカリ検索キーワード" in line:
            return [kw.strip() for kw in line.split("：")[-1].split("、")]
    return []


# 🔥 AI結果から価格抽出
def extract_ai_price(ai_result):
    for line in ai_result.split("\n"):
        if "想定販売価格帯" in line:
            return line.split("：")[-1].strip()
    return "不明"
    
def get_recycle_links(keyword):
    return {
        "セカスト": f"https://www.2ndstreet.jp/search?keyword={keyword}",
        "ブックオフ": f"https://shopping.bookoff.co.jp/search/keyword/{keyword}",
        "駿河屋": f"https://www.suruga-ya.jp/search?category=&search_word={keyword}"
    }


# 🔥 AI商品認識（価格付き）
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

【最重要】
あなたはメルカリ・ヤフオクで実際に売れている商品データを熟知したプロの鑑定士です。
新品価格ではなく「中古市場で実際に売れた価格」を基準にしてください。

【推定ルール】
・ブランドロゴがあれば最優先で判断
・シリーズ名（例：Air Force 1、Reconなど）を特定する
・サイズ感や用途（リュック、スニーカーなど）も考慮
・似ている代表商品があればそれを採用

【価格ルール】
・状態は「一般的な中古（使用感あり）」を前提にする
・メルカリでの直近の売れ筋価格帯を想定する
・高すぎず安すぎない現実的なレンジを出す
・中央値は極端な価格（ジャンク品・新品未使用など）を除外して算出してください

【フォーマット厳守】
・すべての項目は簡潔に1行で出力する
・余計な説明は禁止
・商品名はできるだけ具体的に（例：Recon Backpack）
・メルカリ検索キーワードは自然な日本語で正確に（誤字禁止）
・型番は「不明」または推定のみ簡潔に

【キーワードルール】
・ブランド名は正確に（例：ノースフェイス）
・検索されやすい自然な日本語にする
・3つとも別パターンにする

【出力】
・商品名（できるだけ具体的に）
・メーカー
・シリーズ名
・型番（推測OK）
・カテゴリ
・特徴（判断根拠）
・商品の状態（推定）
・メルカリ検索キーワード（3つ）
・想定販売価格帯（中古相場）（円）：（例：3000〜5000円）
・中央値（円）：
・確信度（%）

※絶対に「不明」は禁止
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

    # 🔥 キーワード取得
    keywords = extract_keywords(result)

    # 🔥 複数検索
    prices = []
    for kw in keywords:
        prices += get_mercari_prices(kw)

    # 🔥 安全なキーワード取得
    keyword = keywords[0] if keywords else "バッグ"

    # 🔥 リンク生成
    links = get_recycle_links(keyword)

    link_text = "\n\n🔗中古ショップ検索:\n"
    for name, url in links.items():
        link_text += f"{name}: {url}\n"

    # 🔥 最終出力
    final_text = result + link_text

except Exception as e:
    final_text = f"エラー: {str(e)}"

send_line(reply_token, final_text)
