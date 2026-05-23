import requests
import time
import base64
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_server():
    HTTPServer(("0.0.0.0", 10000), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

BOT_TOKEN = "8389956727:AAHSdJ-XLiuTp-gZAR-9a1ttV86v5w8AqP0"
GEMINI_KEY = "AIzaSyBA6yxZW0W0j8oFHZTFC3k5NpkD23ctPr8"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYSTEM = """أنت مصحح مقالات عربية تسمى نقطة. صحح المقالات وفق هذه المعايير بدقة:

الفكرة (6 علامات):
- العنوان مناسب: 1 علامة
- وضوح الأفكار (فكرتان على الأقل): 2 علامتان
- ذكر الأدلة أو الشواهد أو الحجج: 1 علامة
- عرض رأي مؤيد أو معارض: 1 علامة
- ذكر رأي الكاتب: 1 علامة

الأساليب (6 علامات):
- توظيف الأساليب اللغوية (أسلوبان على الأقل): 2 علامتان
- تقسيم الموضوع إلى ثلاث فقرات على الأقل: 3 علامات
- توظيف الصور المجازية (يكفي صورة واحدة): 1 علامة

اللغة (3 علامات):
- استخدام علامات الترقيم (علامتان على الأقل): 2 علامتان
- سلامة اللغة وخلوها من الأخطاء: 1 علامة

اعطِ درجة من 15 وفصّل كل معيار بوضوح."""

user_states = {}

def send(chat_id, text):
    requests.post(f"{TG_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })

def get_file_url(file_id):
    r = requests.get(f"{TG_URL}/getFile", params={"file_id": file_id})
    data = r.json()
    file_path = data["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

def download_image(url):
    r = requests.get(url)
    return base64.b64encode(r.content).decode("utf-8")

def ask_gemini_text(messages):
    parts = [{"text": "SYSTEM: " + SYSTEM + "\n\n"}]
    for m in messages:
        role = "USER: " if m["role"] == "user" else "ASSISTANT: "
        parts.append({"text": role + m["content"] + "\n"})
    r = requests.post(GEMINI_URL, json={
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1500}
    })
    data = r.json()
    print("Gemini text response:", data)
    return data["candidates"][0]["content"]["parts"][0]["text"]

def ask_gemini_image(image_b64, mime_type="image/jpeg"):
    parts = [
        {"text": SYSTEM + "\n\nاقرأ نص المقال من الصورة ثم صححه وفق المعايير وأعط درجة من 15:"},
        {"inline_data": {"mime_type": mime_type, "data": image_b64}}
    ]
    r = requests.post(GEMINI_URL, json={
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1500}
    })
    data = r.json()
    print("Gemini image response:", data)
    return data["candidates"][0]["content"]["parts"][0]["text"]

def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    r = requests.get(f"{TG_URL}/getUpdates", params=params, timeout=35)
    return r.json()

offset = None
print("البوت شغال مع دعم الصور...")

while True:
    try:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            if not chat_id:
                continue

            text = msg.get("text", "")
            photo = msg.get("photo")
            document = msg.get("document")

            if text == "/start":
                user_states[chat_id] = []
                send(chat_id, "مرحباً! أنا *نقطة* 🤖\n\nأرسل لي *نص المقال* أو *صورة* منه وسأصححه فوراً!\n\nالدرجة الكلية من 15 ✅")
                continue

            if photo:
                send(chat_id, "⏳ جاري قراءة الصورة وتصحيح المقال...")
                try:
                    file_id = photo[-1]["file_id"]
                    url = get_file_url(file_id)
                    image_b64 = download_image(url)
                    reply = ask_gemini_image(image_b64, "image/jpeg")
                    if chat_id not in user_states:
                        user_states[chat_id] = []
                    user_states[chat_id].append({"role": "user", "content": "[صورة مقال]"})
                    user_states[chat_id].append({"role": "assistant", "content": reply})
                    send(chat_id, reply)
                except Exception as e:
                    traceback.print_exc()
                    send(chat_id, f"❌ حدث خطأ: {str(e)}")

            elif document and document.get("mime_type", "").startswith("image/"):
                send(chat_id, "⏳ جاري قراءة الصورة وتصحيح المقال...")
                try:
                    file_id = document["file_id"]
                    url = get_file_url(file_id)
                    image_b64 = download_image(url)
                    mime = document.get("mime_type", "image/jpeg")
                    reply = ask_gemini_image(image_b64, mime)
                    if chat_id not in user_states:
                        user_states[chat_id] = []
                    user_states[chat_id].append({"role": "user", "content": "[صورة مقال]"})
                    user_states[chat_id].append({"role": "assistant", "content": reply})
                    send(chat_id, reply)
                except Exception as e:
                    traceback.print_exc()
                    send(chat_id, f"❌ حدث خطأ: {str(e)}")

            elif text:
                if chat_id not in user_states:
                    user_states[chat_id] = []
                send(chat_id, "⏳ جاري التصحيح...")
                try:
                    user_states[chat_id].append({"role": "user", "content": text})
                    reply = ask_gemini_text(user_states[chat_id])
                    user_states[chat_id].append({"role": "assistant", "content": reply})
                    send(chat_id, reply)
                except Exception as e:
                    traceback.print_exc()
                    send(chat_id, f"❌ حدث خطأ: {str(e)}")

    except Exception as e:
        traceback.print_exc()
        time.sleep(5)
