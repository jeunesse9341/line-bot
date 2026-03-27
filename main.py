from fastapi import FastAPI, Request
import requests

app = FastAPI()

LINE_TOKEN = "SJf2O2LASoEHeetmLRbxF/8miebqmnuNHD8y7PHV5zqDykovIDJQ/IyxzhgasdthCMgwpZq3ZQUVVd7rXW/kvJg6C6rBH4uYNGQsGsC7jbS4cE4N5MKmS0Mdu7VXfZ1yfjqqlox22hNuGlU2+JVchwdB04t89/1O/w1cDnyilFU="

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()

    for event in body["events"]:
        if event["type"] == "message":
            reply_token = event["replyToken"]

            send_line(reply_token, "動いた🔥")

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