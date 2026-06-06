# ─────────────────────────────────────────
# JARVIS V2 — SYSTEM MODULE
# Full system control: apps, stats, files, power
# ─────────────────────────────────────────
import os
import sys
import platform
import subprocess
import psutil
import shutil
import datetime
import pyautogui
from rich.console import Console
from rich.table import Table

console = Console()
OS = platform.system()  # "Windows" or "Linux"

# ── APP LAUNCHER ──────────────────────────
APP_MAP = {
    # Windows
    "chrome":     "start chrome",
    "firefox":    "start firefox",
    "notepad":    "notepad",
    "calculator": "calc",
    "explorer":   "explorer",
    "vscode":     "code",
    "cmd":        "start cmd",
    "task manager": "taskmgr",
    # Linux
    "gedit":      "gedit",
    "nautilus":   "nautilus",
    "terminal":   "gnome-terminal",
}

def open_app(app_name: str) -> str:
    name = app_name.lower().strip()
    cmd = APP_MAP.get(name)
    if not cmd:
        # Try to run directly
        cmd = name
    try:
        if OS == "Windows":
            os.system(cmd)
        else:
            subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"✅ '{app_name}' open kar diya!"
    except Exception as e:
        return f"❌ '{app_name}' open nahi hua: {e}"

def close_app(app_name: str) -> str:
    name = app_name.lower().strip()
    try:
        if OS == "Windows":
            os.system(f"taskkill /f /im {name}.exe")
        else:
            os.system(f"pkill -f {name}")
        return f"✅ '{app_name}' band kar diya!"
    except Exception as e:
        return f"❌ Error: {e}"

# ── SYSTEM STATS ──────────────────────────
def get_system_stats() -> tuple:
    cpu    = psutil.cpu_percent(interval=1)
    ram    = psutil.virtual_memory()
    disk   = psutil.disk_usage('/')
    bat    = psutil.sensors_battery()
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())

    table = Table(title="💻 System Status", style="cyan", header_style="bold magenta")
    table.add_column("Component", style="white")
    table.add_column("Status", style="green")

    table.add_row("🖥️  CPU Usage",    f"{cpu}%")
    table.add_row("🧠 RAM Used",      f"{ram.used / 1e9:.1f} GB / {ram.total / 1e9:.1f} GB ({ram.percent}%)")
    table.add_row("💾 Disk Used",     f"{disk.used / 1e9:.1f} GB / {disk.total / 1e9:.1f} GB ({disk.percent}%)")
    table.add_row("🔋 Battery",       f"{bat.percent}% {'🔌 Charging' if bat.power_plugged else '🔋 On Battery'}" if bat else "N/A")
    table.add_row("⏱️  Uptime",        str(uptime).split('.')[0])
    table.add_row("🖥️  OS",           f"{platform.system()} {platform.release()}")

    summary = f"CPU {cpu}%, RAM {ram.percent}%, Disk {disk.percent}%"
    return table, summary

def get_running_processes(top_n=10) -> Table:
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except Exception:
            pass

    procs = sorted(procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:top_n]

    table = Table(title=f"🔄 Top {top_n} Processes", style="cyan", header_style="bold yellow")
    table.add_column("PID",  style="dim", width=8)
    table.add_column("Name", style="white")
    table.add_column("CPU%", style="red")
    table.add_column("RAM%", style="magenta")

    for p in procs:
        table.add_row(str(p['pid']), p['name'], f"{p['cpu_percent']:.1f}", f"{p['memory_percent']:.1f}")

    return table

def kill_process(pid: int) -> str:
    try:
        p = psutil.Process(pid)
        p.kill()
        return f"✅ Process {pid} kill kar diya!"
    except Exception as e:
        return f"❌ Error: {e}"

# ── FILE / FOLDER OPS ─────────────────────
def list_directory(path: str = ".") -> tuple:
    try:
        items = os.listdir(path)
    except Exception as e:
        return None, f"❌ Error: {e}"

    table = Table(title=f"📁 {os.path.abspath(path)}", style="cyan", header_style="bold blue")
    table.add_column("Type", width=5)
    table.add_column("Name", style="white")
    table.add_column("Size", style="yellow")

    for item in sorted(items):
        full = os.path.join(path, item)
        if os.path.isdir(full):
            table.add_row("📁", item, "—")
        else:
            sz = os.path.getsize(full)
            size_str = f"{sz/1e6:.2f} MB" if sz > 1e6 else f"{sz/1e3:.1f} KB" if sz > 1e3 else f"{sz} B"
            table.add_row("📄", item, size_str)

    return table, f"{len(items)} items in {path}"

def create_folder(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder banaya: {path}"
    except Exception as e:
        return f"❌ Error: {e}"

def delete_file(path: str) -> str:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"🗑️ Delete kar diya: {path}"
    except Exception as e:
        return f"❌ Error: {e}"

def copy_file(src: str, dst: str) -> str:
    try:
        shutil.copy2(src, dst)
        return f"✅ Copy ho gaya: {src} → {dst}"
    except Exception as e:
        return f"❌ Error: {e}"

def move_file(src: str, dst: str) -> str:
    try:
        shutil.move(src, dst)
        return f"✅ Move ho gaya: {src} → {dst}"
    except Exception as e:
        return f"❌ Error: {e}"

def open_file_or_folder(path: str) -> str:
    try:
        if OS == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
        return f"✅ Opened: {path}"
    except Exception as e:
        return f"❌ Error: {e}"

# ── SCREENSHOT ────────────────────────────
def take_screenshot(save_dir: str = "exports") -> str:
    os.makedirs(save_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(save_dir, f"screenshot_{ts}.png")
    try:
        img = pyautogui.screenshot()
        img.save(path)
        return f"📸 Screenshot saved: {os.path.abspath(path)}"
    except Exception as e:
        return f"❌ Screenshot error: {e}"

# ── POWER CONTROLS ────────────────────────
def shutdown(delay: int = 0) -> str:
    if OS == "Windows":
        os.system(f"shutdown /s /t {delay}")
    else:
        os.system(f"shutdown -h +{delay//60}" if delay else "shutdown -h now")
    return f"⚡ System shutdown in {delay}s..."

def restart(delay: int = 0) -> str:
    if OS == "Windows":
        os.system(f"shutdown /r /t {delay}")
    else:
        os.system("reboot")
    return f"🔄 Restarting system..."

def lock_screen() -> str:
    if OS == "Windows":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    else:
        os.system("gnome-screensaver-command -l")
    return "🔒 Screen lock kar diya!"

def get_ip_info() -> str:
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return f"🌐 Hostname: {hostname} | Local IP: {local_ip}"

def get_wifi_info() -> str:
    try:
        if OS == "Windows":
            out = subprocess.check_output("netsh wlan show interfaces", shell=True).decode()
            for line in out.split("\n"):
                if "SSID" in line and "BSSID" not in line:
                    return f"📶 WiFi: {line.strip()}"
        else:
            out = subprocess.check_output("iwgetid -r", shell=True).decode().strip()
            return f"📶 WiFi: {out}"
    except Exception:
        pass
    return "📶 WiFi info unavailable"
