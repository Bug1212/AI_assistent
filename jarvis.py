#!/usr/bin/env python3
"""
JARVIS V2 — Personal AI Assistant
By: NPT Solutions / Tarun (Bunty)
Voice + Telegram + System Control + Weather + Tasks + Web Search
"""

import os, sys, json, threading, datetime, re
import requests as _req
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

import config
from modules.voice        import speak, listen
from modules.tasks        import (add_task, list_tasks, update_task_status,
                                   delete_task, add_note, list_notes,
                                   add_reminder, list_reminders,
                                   check_reminders, export_tasks, init_db)
from modules.system       import (open_app, close_app, get_system_stats,
                                   get_running_processes, kill_process,
                                   list_directory, create_folder, delete_file,
                                   copy_file, move_file, take_screenshot,
                                   shutdown, restart, lock_screen,
                                   get_ip_info, get_wifi_info, open_file_or_folder)
from modules.telegram_bot import bot_send, bot_send_file, start_bot_polling

console = Console()
groq_client = Groq(api_key=config.GROQ_API_KEY)

# ─────────────────────────────────────────
# WEB SEARCH — Groq built-in tool (most reliable)
# ─────────────────────────────────────────
def web_search(query: str) -> str:
    """Groq ke built-in web_search tool se search karo — no extra API needed"""
    try:
        resp = groq_client.chat.completions.create(
            model=config.GROQ_SEARCH_MODEL,  # groq/compound — built-in web search
            messages=[
                {"role": "system", "content": "You are a search assistant. Search the web and return factual, concise results in plain text. Include source info when available."},
                {"role": "user", "content": f"Search for: {query}"}
            ],
            max_tokens=600,
        )
        result = resp.choices[0].message.content.strip()

        # Also grab any tool execution metadata if present
        if hasattr(resp.choices[0].message, 'tool_calls') and resp.choices[0].message.tool_calls:
            pass  # content already has the answer

        return result if result else "Koi result nahi mila."
    except Exception as e:
        # Fallback: scrape Google via requests
        return _google_scrape_fallback(query)

def _google_scrape_fallback(query: str) -> str:
    """Fallback: Google search snippet scrape"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
        r = _req.get(
            "https://www.google.com/search",
            params={"q": query, "num": 5},
            headers=headers, timeout=8
        )
        # Extract featured snippet / descriptions
        snippets = re.findall(r'<div class="BNeawe[^"]*"[^>]*>(.*?)</div>', r.text)
        clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets if len(s) > 40]
        unique = list(dict.fromkeys(clean))[:4]
        if unique:
            return "\n".join(f"- {s}" for s in unique)
        return "Search results nahi aaye. Network check karo."
    except Exception as e:
        return f"Search failed: {e}"

# ─────────────────────────────────────────
# WEATHER
# ─────────────────────────────────────────
def get_weather(city: str = None) -> str:
    city = city or config.DEFAULT_CITY
    try:
        r = _req.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": config.OPENWEATHER_API_KEY, "units": "metric"},
            timeout=8
        )
        d = r.json()
        if r.ok:
            return (f"🌤️ {city}: {d['main']['temp']}°C (feels {d['main']['feels_like']}°C)\n"
                    f"   {d['weather'][0]['description'].capitalize()} | "
                    f"Humidity {d['main']['humidity']}% | Wind {d['wind']['speed']} m/s")
        return f"Weather error: {d.get('message','Unknown')}"
    except Exception as e:
        return f"Weather fetch failed: {e}"

# ─────────────────────────────────────────
# AI BRAIN — SMARTER SYSTEM PROMPT
# ─────────────────────────────────────────
SYSTEM_PROMPT = """You are JARVIS, a smart personal AI assistant for Tarun (NPT Solutions, Pune).
You speak Hinglish — casual, direct, like a smart friend. No unnecessary questions.

## BEHAVIOR RULES (CRITICAL):
1. **Search karo pehle, pucho baad mein** — agar koi bhi factual/internet question ho, web_search action use karo automatically. Kabhi mat kaho "mujhe nahi pata, aap search karo".
2. **Personal assistant ki tarah kaam karo** — kaam karo, phir brief confirmation do. Unnecessary clarifying questions mat pucho.
3. **Listing default OFF** — sirf tab list karo jab user ne explicitly manga ho ya multiple options ho.
4. **Ek follow-up allowed** — kaam karne ke baad ek short follow-up question allowed hai jaise "Kuch aur chahiye?" — but only after completing the task.
5. **NPT Solutions = Tarun ka web dev agency, Pune mein hai** — yeh general knowledge rakho.

## ACTION FORMAT:
Jab action lena ho, sirf JSON respond karo. General chat mein normal Hinglish text.

ACTIONS:
Search/Info:
  {"action":"web_search","query":"..."}

Tasks:
  {"action":"add_task","title":"...","priority":"high/medium/low","due_date":"YYYY-MM-DD or empty"}
  {"action":"list_tasks","status":"all/pending/done"}
  {"action":"complete_task","id":<int>}
  {"action":"delete_task","id":<int>}

Notes:
  {"action":"add_note","content":"..."}
  {"action":"list_notes"}

Reminders:
  {"action":"add_reminder","title":"...","time":"HH:MM or YYYY-MM-DD HH:MM"}
  {"action":"list_reminders"}

Export:
  {"action":"export_tasks","format":"excel/csv"}

System:
  {"action":"open_app","app":"..."}
  {"action":"close_app","app":"..."}
  {"action":"system_stats"}
  {"action":"processes"}
  {"action":"kill_process","pid":<int>}
  {"action":"screenshot"}
  {"action":"lock_screen"}
  {"action":"shutdown","delay":<seconds>}
  {"action":"restart"}
  {"action":"ip_info"}
  {"action":"wifi_info"}
  {"action":"list_dir","path":"..."}
  {"action":"create_folder","path":"..."}
  {"action":"delete_file","path":"..."}
  {"action":"open_path","path":"..."}

Weather:
  {"action":"weather","city":"..."}

Telegram:
  {"action":"telegram_send","message":"..."}
  {"action":"telegram_send_to","recipient":"@username or +91number","message":"..."}
  {"action":"telegram_file","path":"...","caption":"..."}

Datetime:
  {"action":"datetime"}

## SEARCH EXAMPLES:
User: "aifeed24.com ka owner kaun hai" → {"action":"web_search","query":"aifeed24.com owner whois"}
User: "what is GPT-5" → {"action":"web_search","query":"GPT-5 latest news 2026"}
User: "bitcoin price" → {"action":"web_search","query":"bitcoin price today"}
User: "NPT Solutions kya hai" → respond from knowledge (Tarun ka agency)
User: "open chrome" → {"action":"open_app","app":"chrome"}
"""

history = []

def ask_jarvis(user_input: str) -> str:
    history.append({"role": "user", "content": user_input})
    resp = groq_client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history[-20:],
        temperature=0.3,
        max_tokens=700
    )
    reply = resp.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    return reply

def ask_jarvis_with_context(user_input: str, context: str) -> str:
    """Search result ke baad JARVIS se answer generate karo"""
    prompt = f"""User ne poocha: "{user_input}"

Search results:
{context}

Yeh results dekh ke user ko direct, useful answer do Hinglish mein. 
Short rakho, important points highlight karo. Ek follow-up question allowed hai end mein."""
    resp = groq_client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500
    )
    return resp.choices[0].message.content.strip()

# ─────────────────────────────────────────
# ACTION HANDLER
# ─────────────────────────────────────────
def handle_action(reply: str, original_input: str = "") -> tuple:
    try:
        s = reply.find("{"); e = reply.rfind("}") + 1
        if s == -1:
            return None, reply  # plain chat

        data   = json.loads(reply[s:e])
        action = data.get("action", "")

        # ── WEB SEARCH ──
        if action == "web_search":
            query = data.get("query", original_input)
            with console.status(f"[cyan]Searching: {query}...[/cyan]"):
                results = web_search(query)
            if "nahi mili" in results or "error" in results.lower():
                return None, f"Kuch nahi mila '{query}' ke liye. Try differently?"
            # Feed results back to JARVIS for a smart answer
            smart_answer = ask_jarvis_with_context(original_input, results)
            return None, smart_answer

        # ── TASKS ──
        elif action == "add_task":
            return None, add_task(data.get("title","Task"), "", data.get("priority","medium"), data.get("due_date",""))
        elif action == "list_tasks":
            return list_tasks(data.get("status","all"))
        elif action == "complete_task":
            return None, update_task_status(data["id"], "done")
        elif action == "delete_task":
            return None, delete_task(data["id"])
        elif action == "add_note":
            return None, add_note(data["content"])
        elif action == "list_notes":
            return list_notes()
        elif action == "add_reminder":
            return None, add_reminder(data["title"], data["time"])
        elif action == "list_reminders":
            return list_reminders()
        elif action == "export_tasks":
            result = export_tasks(data.get("format","excel"))
            if "exports" in result:
                path = result.split(": ")[-1].strip()
                try: bot_send_file(path, "📁 Exported Tasks")
                except: pass
            return None, result

        # ── SYSTEM ──
        elif action == "open_app":
            return None, open_app(data["app"])
        elif action == "close_app":
            return None, close_app(data["app"])
        elif action == "system_stats":
            return get_system_stats()
        elif action == "processes":
            return get_running_processes(), "Top running processes:"
        elif action == "kill_process":
            return None, kill_process(data["pid"])
        elif action == "screenshot":
            result = take_screenshot()
            if "saved" in result:
                path = result.split(": ")[-1].strip()
                try: bot_send_file(path, "📸 Screenshot")
                except: pass
            return None, result
        elif action == "lock_screen":
            return None, lock_screen()
        elif action == "shutdown":
            return None, shutdown(data.get("delay", 0))
        elif action == "restart":
            return None, restart()
        elif action == "ip_info":
            return None, get_ip_info()
        elif action == "wifi_info":
            return None, get_wifi_info()
        elif action == "list_dir":
            return list_directory(data.get("path", "."))
        elif action == "create_folder":
            return None, create_folder(data["path"])
        elif action == "delete_file":
            return None, delete_file(data["path"])
        elif action == "open_path":
            return None, open_file_or_folder(data["path"])

        # ── WEATHER ──
        elif action == "weather":
            return None, get_weather(data.get("city"))

        # ── TELEGRAM ──
        elif action == "telegram_send":
            return None, bot_send(data["message"])
        elif action == "telegram_send_to":
            try:
                from modules.telegram_user import user_send_message
                return None, user_send_message(data["recipient"], data["message"])
            except ImportError:
                return None, "Telethon module enable karo pehle."
        elif action == "telegram_file":
            return None, bot_send_file(data["path"], data.get("caption",""))

        # ── DATETIME ──
        elif action == "datetime":
            now = datetime.datetime.now().strftime("%A, %d %B %Y — %I:%M %p")
            return None, f"🕐 {now}"

        else:
            return None, reply

    except (json.JSONDecodeError, KeyError):
        return None, reply

# ─────────────────────────────────────────
# PROCESS COMMAND
# ─────────────────────────────────────────
def process_command(user_input: str, via_voice: bool = False) -> str:
    try:
        reply = ask_jarvis(user_input)
        table, msg = handle_action(reply, user_input)
        if table:
            console.print(table)
        console.print(f"\n[bold cyan]JARVIS:[/bold cyan] {msg}\n")
        if via_voice:
            clean = re.sub(r'[^\x00-\x7F]+', '', msg)
            speak(clean[:250], silent=False)
        return msg
    except Exception as e:
        err = f"Error: {e}"
        console.print(f"[red]{err}[/red]")
        return err

# ─────────────────────────────────────────
# HELP
# ─────────────────────────────────────────
def print_help():
    console.print(Panel("""[bold]🔍 Search (auto):[/bold]
  Kuch bhi pucho — JARVIS khud search karega
  "aifeed24.com owner kaun hai"
  "bitcoin price today"
  "latest news about AI"

[bold]💻 System:[/bold]  open chrome | system stats | screenshot | lock screen
[bold]📋 Tasks:[/bold]   add task, list tasks, complete task 3, delete task 2
[bold]📝 Notes:[/bold]   save note: xyz | show notes
[bold]⏰ Remind:[/bold]  remind me at 18:00 to call client
[bold]🌤️ Weather:[/bold] weather in Mumbai
[bold]📱 Telegram:[/bold]
  send telegram: hello
  send to @username: message
[bold]📁 Files:[/bold]   list files in D:/ | create folder test
[bold]📁 Export:[/bold]  export tasks to excel
[bold]🎙️ Voice:[/bold]   'v' to toggle voice mode
[bold]🚪 Exit:[/bold]    exit / quit / bye""",
        title="JARVIS V2 Commands", border_style="yellow"))

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    os.makedirs("database", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    init_db()

    threading.Thread(target=check_reminders, daemon=True).start()
    start_bot_polling(lambda cmd: process_command(cmd))

    console.clear()
    console.print(Panel.fit(
        "[bold cyan]J.A.R.V.I.S  V2[/bold cyan]\n[dim]Voice + Search + Telegram + System — NPT Solutions[/dim]",
        border_style="cyan"
    ))
    try:
        bot_send("🤖 *JARVIS V2 Online!* Ready sir.")
    except Exception:
        pass
    console.print("[dim]Type 'help' for commands | 'v' for voice | 'exit' to quit[/dim]\n")

    voice_mode = False

    while True:
        try:
            if voice_mode:
                console.print("[bold yellow]🎙️  Listening...[/bold yellow]")
                user_input = listen(timeout=6)
                if not user_input:
                    continue
            else:
                user_input = Prompt.ask("[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            speak("Goodbye sir!", silent=True)
            try: bot_send("🔴 JARVIS offline.")
            except: pass
            break

        if not user_input:
            continue

        low = user_input.lower()
        if low in ["exit", "quit", "bye"]:
            console.print("[cyan]JARVIS: Goodbye sir! 👋[/cyan]")
            try: bot_send("🔴 JARVIS offline.")
            except: pass
            break
        elif low == "help":
            print_help()
        elif low == "v":
            voice_mode = not voice_mode
            status = "ON 🎙️" if voice_mode else "OFF ⌨️"
            console.print(f"[yellow]Voice mode: {status}[/yellow]")
        else:
            process_command(user_input, via_voice=voice_mode)

if __name__ == "__main__":
    main()