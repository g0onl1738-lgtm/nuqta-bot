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

user_states = {}

def send(chat_id, text):
    requests.post(f"{TG_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_url(file_id):
    r = requests.get(f"{TG_URL}/getFile", params={"file_id": file_id})
    file_path = r.json()["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

def download_image(url):
    r = requests.get(url)
    return base64.b64encode(r.content).decode("utf-8")

def ask_gemini_image(image_b64):
    prompt = """اقرأ نص المقال العربي من هذه الصورة بدقة، ثم صححه وفق المعايير التالية وأعط درجة من 15:

الفكرة (6 علامات): العنوان مناسب(1) + وضوح الأفكار(2) + الأدلة(1) + رأي مؤيد/معارض(1) + رأي الكاتب(1)
الأساليب (6 علامات): الأساليب اللغوية(2) + تقسيم الفقرات(3) + الصور المجازية(1)
اللغة (3 علامات): علامات الترقيم(2) + سلامة اللغة(1)

اكتب النتيجة هكذا:
الدرجة الكلية: X/15
الفكرة: X/6
الأساليب: X/6
اللغة: X/3
ملاحظات: ..."""

    r = requests.post(GEMINI_URL, json={
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
        ]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
    })
    data = r.json()
    print("Response:", data)
    if not data.get("candidates"):
        feedback = data.get("promptFeedback", {})
        raise Exception(f"رُفضت الصورة: {feedback}")
    return data["candidates"][0]["content"]["parts"][0]["text"]

def ask_gemini_text(text):
    prompt = f"""صحح هذا المقال العربي وفق المعايير التالية وأعط درجة من 15:

الفكرة (6 علامات): العنوان مناسب(1) + وضوح الأفكار(2) + الأدلة(1) + رأي مؤيد/معارض(1) + رأي الكاتب(1)
الأساليب (6 علامات): الأساليب اللغوية(2) + تقسيم الفقرات(3) + الصور المجازية(1)
اللغة (3 علامات): علامات الترقيم(2) + سلامة اللغة(1)

المقال:
{text}

اكتب النتيجة هكذا:
الدرجة الكلية: X/15
الفكرة: X/6
الأساليب: X/6
اللغة: X/3
ملاحظات: ..."""

    r = requests.post(GEMINI_URL, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
    })
    data = r.json()
    print("Response:", data)
    if not data.get("candidates"):
        raise Exception("لم يرد Gemini")
    return data["candidates"][0]["content"]["parts"][0]["text"]

def get_updates(offset=None):
    r = requests.get(f"{TG_URL}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=35)
    return r.json()

offset = None
print("البوت شغال...")

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

            if text == "/start":
                send(chat_id, "مرحباً! أنا نقطة 🤖\nأرسل صورة المقال أو النص وسأصححه فوراً!\nالدرجة من 15 ✅")
                continue

            if photo:
                send(chat_id, "⏳ جاري قراءة الصورة...")
                try:
                    file_id = photo[-1]["file_id"]
                    url = get_file_url(file_id)
                    image_b64 = download_image(url)
                    reply = ask_gemini_image(image_b64)
                    send(chat_id, reply)
                except Exception as e:
                    traceback.print_exc()
                    send(chat_id, f"❌ خطأ: {str(e)}")

            elif text:
                send(chat_id, "⏳ جاري التصحيح...")
                try:
                    reply = ask_gemini_text(text)
                    send(chat_id, reply)
                except Exception as e:
                    traceback.print_exc()
                    send(chat_id, f"❌ خطأ: {str(e)}")

    except Exception as e:
        traceback.print_exc()
        time.sleep(5)
