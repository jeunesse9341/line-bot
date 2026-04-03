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
    
from urllib.parse import quote

def normalize_category(category):
    if not category:
        return ""

    # カテゴリ統一（ここ重要）
    if "リュック" in category or "バックパック" in category:
        return "バックパック"
    if "靴" in category or "スニーカー" in category:
        return "スニーカー"
    if "ジャケット" in category or "アウター" in category:
        return "ジャケット"

    return category


def build_best_keyword(ai_result):
    brand = ""
    series = ""
    category = ""

    for line in ai_result.split("\n"):
        line = line.strip()

        # 完全一致で抽出（ここが超重要）
        if line.startswith("- メーカー"):
            brand = line.split("：")[-1].strip()

        elif line.startswith("- シリーズ名"):
            series = line.split("：")[-1].strip()

        elif line.startswith("- カテゴリ"):
            category = line.split("：")[-1].strip()

    # カテゴリ補正
    category = normalize_category(category)

    # 最強パターン（これがメイン）
    if brand and series and category:
        return f"{brand} {series} {category}"

    # 次点
    if brand and category:
        return f"{brand} {category}"

    # 最低限
    if brand:
        return brand

    return "バッグ"


def encode_keyword(keyword):
    return quote(keyword)
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
from urllib.parse import quote


def normalize_category(category):
    if not category:
        return ""

    if "リュック" in category or "バックパック" in category:
        return "バックパック"
    if "靴" in category or "スニーカー" in category:
        return "スニーカー"
    if "ジャケット" in category or "アウター" in category:
        return "ジャケット"

    return category

import re

def extract_purchase_price(ai_result):
    for line in ai_result.split("\n"):
        if "仕入れ価格" in line:
            nums = re.findall(r"\d+", line)
            if nums:
                return int(nums[0])
    return None
    
def build_best_keyword(ai_result):
    brand = ""
    series = ""
    category = ""

    for line in ai_result.split("\n"):
        line = line.strip()

        if line.startswith("- メーカー"):
            brand = line.split("：")[-1].strip()

        elif line.startswith("- シリーズ名"):
            series = line.split("：")[-1].strip()

        elif line.startswith("- カテゴリ"):
            category = line.split("：")[-1].strip()

    # カテゴリ補正
    category = normalize_category(category)

    # 最強キーワード生成
    if brand and series and category:
        return f"{brand} {series} {category}"

    if brand and category:
        return f"{brand} {category}"

    if brand:
        return brand

    return "バッグ"


def encode_keyword(keyword):
    return quote(keyword)


def get_recycle_links(keyword):
    encoded = encode_keyword(keyword)

    return {
        "セカスト": f"https://www.2ndstreet.jp/search?keyword={encoded}",
        "ブックオフ": f"https://shopping.bookoff.co.jp/search/keyword/{encoded}",
        "駿河屋": f"https://www.suruga-ya.jp/search?search_word={encoded}"
    }    
def get_recycle_links(keyword):
    encoded = encode_keyword(keyword)

    return {
        "セカスト": f"https://www.2ndstreet.jp/search?keyword={encoded}",
        "ブックオフ": f"https://shopping.bookoff.co.jp/search/keyword/{encoded}",
        "駿河屋": f"https://www.suruga-ya.jp/search?search_word={encoded}"
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

【追加】
画像内に値札や価格表示がある場合は、その金額を必ず読み取ってください。
「仕入れ価格（円）：〇〇」として出力してください。
値札が無い場合はこの項目は出力しないでください。

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

                # 🔥ここからtry（インデント超重要）
                try:
                    result = recognize_product("image.jpg")

                    import re

                    # 🔥 中央値取得
                    median_price = 0
                    for line in result.split("\n"):
                        if "中央値" in line:
                            nums = re.findall(r"\d+", line)
                            if nums:
                                median_price = int(nums[0])

                    # 🔥 仕入れ価格取得
                    purchase_price = None
                    for line in result.split("\n"):
                        if "仕入れ価格" in line:
                            nums = re.findall(r"\d+", line)
                            if nums:
                                purchase_price = int(nums[0])

                    # 🔥 利益計算
                    profit_text = ""
                    if purchase_price and median_price:
                        fee = int(median_price * 0.1)
                        shipping = 700
                        profit = median_price - (purchase_price + fee + shipping)

                        profit_text = f"""

【仕入れ価格】
¥{purchase_price}

【利益】
¥{profit}
"""

                    # 🔥 キーワード
                    keyword = build_best_keyword(result)

                    # 🔥 リンク
                    links = get_recycle_links(keyword)

                    link_text = "\n\n🔗中古ショップ検索:\n"
                    for name, url in links.items():
                        link_text += f"{name}: <{url}>\n"

                    final_text = result + profit_text + link_text

                except Exception as e:
                    final_text = f"エラー: {str(e)}"

                send_line(reply_token, final_text)

    return {"status": "ok"}
