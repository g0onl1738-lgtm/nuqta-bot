import requests
import json
import time

BOT_TOKEN = "8389956727:AAHSdJ-XLiuTp-gZAR-9a1ttV86v5w8AqP0"
GEMINI_KEY = "AIzaSyBA6yxZW0W0j8oFHZTFC3k5NpkD23ctPr8"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYSTEM = """أنت مصحح مقالات عربية تسمى نقطة. صحح المقالات وفق هذه المعايير:
الفكرة (6 علامات): العنوان مناسب(1) وضوح الأفكار(2) الأدلة(1) رأي مؤيد/معارض(1) رأي الكاتب(1)
الأساليب (6 علامات): الأساليب اللغوية(2) تقسيم فقرات(3) صور مجازية(1)
اللغة (3 علامات): علامات الترقيم(2) سلامة اللغة(1)
أعط درجة من 15 وفصّل كل معيار."""

user_states = {}

def send(chat_id, text):
    requests.post(f"{TG_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def ask_gemini(messages):
    parts = []
    parts.append({"text": "SYSTEM: " + SYSTEM + "\n\n"})
    for m in messages:
        role = "USER: " if m["role"] == "user" else "ASSISTANT: "
        parts.append({"text": role + m["content"] + "\n"})
    r = requests.post(GEMINI_URL, json={
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1500}
    })
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    r = requests.get(f"{TG_URL}/getUpdates", params=params, timeout=35)
    return r.json()

offset = None
print("البوت شغال...")
send_startup = True

while True:
    try:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            if not chat_id or not text:
                continue
            if text == "/start":
                user_states[chat_id] = []
                send(chat_id, "مرحباً! أنا نقطة 🤖\nأرسل لي نص المقال وسأصححه فوراً حسب معايير التصحيح.\nالدرجة الكلية من 15.")
            else:
                if chat_id not in user_states:
                    user_states[chat_id] = []
                send(chat_id, "⏳ جاري التصحيح...")
                user_states[chat_id].append({"role": "user", "content": text})
                reply = ask_gemini(user_states[chat_id])
                user_states[chat_id].append({"role": "assistant", "content": reply})
                send(chat_id, reply)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
