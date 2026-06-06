# ═══════════════════════════════════════════════════════
# JARVIS V2 — TELEGRAM BOT MODULE (2-way Bot API)
# ═══════════════════════════════════════════════════════
# File: modules/telegram_bot.py
import asyncio
import threading
import requests
from rich.console import Console
import config

console = Console()
BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

# ── SEND MESSAGE ──────────────────────────
def bot_send(msg: str, chat_id: str = None) -> str:
    cid = chat_id or config.TELEGRAM_CHAT_ID
    try:
        r = requests.post(f"{BASE}/sendMessage", json={
            "chat_id": cid,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=10)
        if r.ok:
            return f"✅ Telegram pe bhej diya!"
        return f"❌ Telegram error: {r.text}"
    except Exception as e:
        return f"❌ Error: {e}"

def bot_send_file(file_path: str, caption: str = "") -> str:
    try:
        with open(file_path, 'rb') as f:
            r = requests.post(f"{BASE}/sendDocument", data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "caption": caption
            }, files={"document": f}, timeout=30)
        return "✅ File Telegram pe bhej di!" if r.ok else f"❌ Error: {r.text}"
    except Exception as e:
        return f"❌ Error: {e}"

# ── RECEIVE COMMANDS (polling) ────────────
def start_bot_polling(on_command_callback):
    """
    Background thread mein chalta hai.
    Telegram se commands receive karta hai → on_command_callback(text) call karta hai.
    """
    offset = None

    def _poll():
        nonlocal offset
        while True:
            try:
                params = {"timeout": 30, "allowed_updates": ["message"]}
                if offset:
                    params["offset"] = offset
                r = requests.get(f"{BASE}/getUpdates", params=params, timeout=35)
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    cid  = msg.get("chat", {}).get("id")
                    if text and str(cid) == str(config.TELEGRAM_CHAT_ID):
                        console.print(f"[bold blue]📱 Telegram Command:[/bold blue] {text}")
                        result = on_command_callback(text)
                        if result:
                            bot_send(str(result))
            except Exception as e:
                console.print(f"[dim red]Telegram polling error: {e}[/dim red]")

    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    console.print("[green]📱 Telegram Bot listening...[/green]")

def get_my_chat_id() -> str:
    """Helper: apna chat ID pata karo"""
    try:
        r = requests.get(f"{BASE}/getUpdates").json()
        results = r.get("result", [])
        if results:
            cid = results[-1]["message"]["chat"]["id"]
            return f"Your Chat ID: {cid}"
        return "No messages found. Send any message to your bot first."
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════
# JARVIS V2 — TELEGRAM USER MODULE (Telethon)
# Send to ANYONE on Telegram via your account
# ═══════════════════════════════════════════════════════
# File: modules/telegram_user.py  (import separately)
#
# ⚠️  NOTE: Paste this class into a new file: modules/telegram_user.py
#
# from telethon.sync import TelegramClient
# from telethon import functions
# import config
#
# _client = None
#
# def get_client():
#     global _client
#     if _client is None:
#         _client = TelegramClient(
#             config.TELEGRAM_SESSION,
#             config.TELEGRAM_API_ID,
#             config.TELEGRAM_API_HASH
#         )
#         _client.start(phone=config.TELEGRAM_PHONE)
#     return _client
#
# def user_send_message(recipient: str, message: str) -> str:
#     """
#     recipient: phone number (+91xxxxxxxxxx), username (@username), or contact name
#     message: text to send
#     """
#     try:
#         client = get_client()
#         client.send_message(recipient, message)
#         return f"✅ Message bhej diya '{recipient}' ko!"
#     except Exception as e:
#         return f"❌ Error: {e}"
#
# def user_get_dialogs(n=10) -> list:
#     """Recent chats / contacts list"""
#     try:
#         client = get_client()
#         dialogs = client.get_dialogs(limit=n)
#         return [(d.name, d.entity.id) for d in dialogs]
#     except Exception as e:
#         return []
#
# ═══════════════════════════════════════════════════════
# To enable Telethon:
# 1. pip install telethon
# 2. Uncomment the code above into modules/telegram_user.py
# 3. Get API ID & Hash from: https://my.telegram.org
# 4. Run once to authenticate (OTP on phone)
# ═══════════════════════════════════════════════════════
