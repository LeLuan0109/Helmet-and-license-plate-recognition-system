import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load biến môi trường từ file .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_violation_alert(location: str, rider_url: str, plate_url: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong file .env")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = (
        f"🚨 <b>Phát hiện vi phạm</b> tại <b>{location}</b> lúc <b>{now}</b>\n\n"
        f"🔗 <b>Liên kết chi tiết:</b>\n"
        f"Hình ảnh vi phạm:\n{rider_url}\n"
        f"Hình ảnh biển số:\n{plate_url if plate_url else 'Không có ảnh biển số'}\n"
        f"Mức độ chính xác: <b>Trung bình</b>"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False  # quan trọng để bật preview
    }

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        print("✅ Gửi tin nhắn với preview thành công")
    except requests.RequestException as e:
        print(f"❌ Gửi tin nhắn thất bại: {e}")
