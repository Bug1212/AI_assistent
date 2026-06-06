# ─────────────────────────────────────────
# JARVIS V2 — TASKS MODULE
# Tasks, Notes, Reminders, Export
# ─────────────────────────────────────────
import os
import sqlite3
import datetime
import time
import threading
import pandas as pd
from plyer import notification
from rich.console import Console
from rich.table import Table
import config

console = Console()

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────
def init_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        priority TEXT DEFAULT 'medium',
        created_at TEXT,
        due_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        triggered INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────
def add_task(title, description="", priority="medium", due_date=""):
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute(
        "INSERT INTO tasks (title, description, priority, created_at, due_date) VALUES (?,?,?,?,?)",
        (title, description, priority, now, due_date)
    )
    conn.commit()
    conn.close()
    return f"Task add ho gayi: '{title}' [{priority}]"

def list_tasks(status="all"):
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    if status == "all":
        c.execute("SELECT id, title, status, priority, due_date FROM tasks ORDER BY id DESC")
    else:
        c.execute("SELECT id, title, status, priority, due_date FROM tasks WHERE status=? ORDER BY id DESC", (status,))
    tasks = c.fetchall()
    conn.close()

    if not tasks:
        return None, "Koi task nahi mili."

    table = Table(title="Your Tasks", style="cyan", header_style="bold magenta")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="yellow")
    table.add_column("Due", style="red")

    icons = {"done": "✅", "in-progress": "🔄", "pending": "⏳"}
    for t in tasks:
        icon = icons.get(t[2], "⏳")
        table.add_row(str(t[0]), t[1], f"{icon} {t[2]}", t[3], t[4] or "—")

    return table, f"{len(tasks)} task(s) found."

def update_task_status(task_id, new_status):
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
    conn.commit()
    conn.close()
    return f"Task #{task_id} → '{new_status}' mark ho gaya!"

def delete_task(task_id):
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return f"Task #{task_id} delete ho gayi."

# ─────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────
def add_note(content):
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO notes (content, created_at) VALUES (?,?)", (content, now))
    conn.commit()
    conn.close()
    return "Note save ho gayi!"

def list_notes():
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, content, created_at FROM notes ORDER BY id DESC LIMIT 10")
    notes = c.fetchall()
    conn.close()

    if not notes:
        return None, "Koi note nahi hai."

    table = Table(title="Your Notes", style="cyan", header_style="bold blue")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Note", style="white")
    table.add_column("Saved At", style="yellow")

    for n in notes:
        preview = n[1][:60] + ("..." if len(n[1]) > 60 else "")
        table.add_row(str(n[0]), preview, n[2])

    return table, f"{len(notes)} note(s) found."

# ─────────────────────────────────────────
# REMINDERS
# ─────────────────────────────────────────
def add_reminder(title, remind_at_str):
    try:
        if len(remind_at_str.strip()) == 5:  # HH:MM only
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            remind_at_str = f"{today} {remind_at_str.strip()}"
        datetime.datetime.strptime(remind_at_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return "Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM"

    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reminders (title, remind_at) VALUES (?,?)", (title, remind_at_str))
    conn.commit()
    conn.close()
    return f"Reminder set ho gaya: '{title}' at {remind_at_str}"

def list_reminders():
    conn = sqlite3.connect(config.DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, remind_at, triggered FROM reminders ORDER BY remind_at ASC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return None, "Koi reminder nahi hai."

    table = Table(title="Reminders", style="cyan", header_style="bold yellow")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Title", style="white")
    table.add_column("Time", style="green")
    table.add_column("Status", style="magenta")

    for r in rows:
        status = "Done" if r[3] else "Pending"
        table.add_row(str(r[0]), r[1], r[2], status)

    return table, f"{len(rows)} reminder(s)."

def check_reminders():
    """Runs in background — checks every 30 seconds"""
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            conn = sqlite3.connect(config.DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, title FROM reminders WHERE remind_at<=? AND triggered=0", (now,))
            due = c.fetchall()
            for r in due:
                try:
                    notification.notify(
                        title="JARVIS Reminder",
                        message=r[1],
                        timeout=10
                    )
                except Exception:
                    pass
                console.print(f"\n[bold yellow]REMINDER: {r[1]}[/bold yellow]\n")
                c.execute("UPDATE reminders SET triggered=1 WHERE id=?", (r[0],))
            conn.commit()
            conn.close()
        except Exception:
            pass
        time.sleep(30)

# ─────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────
def export_tasks(fmt="excel"):
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_FILE)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()

    if df.empty:
        return "Koi task nahi hai export karne ke liye."

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    if fmt == "csv":
        path = os.path.join(config.EXPORT_DIR, f"tasks_{ts}.csv")
        df.to_csv(path, index=False)
    else:
        path = os.path.join(config.EXPORT_DIR, f"tasks_{ts}.xlsx")
        df.to_excel(path, index=False)

    return f"Exported: {os.path.abspath(path)}"
