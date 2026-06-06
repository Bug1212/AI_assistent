# ─────────────────────────────────────────
# JARVIS V2 — VOICE MODULE
# Edge TTS — Interruptible, chunked speech
# Press ENTER or speak to interrupt
# ─────────────────────────────────────────
import asyncio
import os
import re
import threading
import tempfile
import speech_recognition as sr
from rich.console import Console
import config

console = Console()
recognizer = sr.Recognizer()

VOICE_EN = "en-IN-NeerjaNeural"  # Indian English — Hinglish ready

# Global stop flag
_stop_speaking = threading.Event()

def _detect_lang(text: str) -> str:
    return VOICE_EN

# ── SPLIT INTO CHUNKS ─────────────────────
def _split_chunks(text: str) -> list[str]:
    """Split long text into sentence-sized chunks for interruptible playback"""
    # Split on . ! ? or newlines
    chunks = re.split(r'(?<=[.!?\n])\s+', text.strip())
    # Merge very short chunks
    merged, buf = [], ""
    for c in chunks:
        buf += " " + c
        if len(buf) > 80:
            merged.append(buf.strip())
            buf = ""
    if buf.strip():
        merged.append(buf.strip())
    return merged if merged else [text]

# ── SPEAK (interruptible) ─────────────────
def speak(text: str, silent: bool = False):
    """JARVIS bolega — chunk by chunk, interruptible anytime"""
    console.print(f"\n[bold cyan]JARVIS:[/bold cyan] {text}\n")
    console.print("[dim]( ENTER dabao bolna rokne ke liye )[/dim]")
    if silent:
        return

    _stop_speaking.clear()
    chunks = _split_chunks(text)

    def _play_chunks():
        for chunk in chunks:
            if _stop_speaking.is_set():
                break
            if not chunk.strip():
                continue
            try:
                asyncio.run(_speak_chunk(chunk, VOICE_EN))
            except Exception as e:
                console.print(f"[dim red]Voice error: {e}[/dim red]")
                break

    # Play in background thread
    t = threading.Thread(target=_play_chunks, daemon=True)
    t.start()

    # Main thread: listen for ENTER to interrupt
    try:
        input()  # Blocks until ENTER pressed
        _stop_speaking.set()
        console.print("[dim yellow]⏹ Voice interrupted.[/dim yellow]")
    except EOFError:
        pass  # Non-interactive mode

    t.join(timeout=3)

async def _speak_chunk(text: str, voice: str):
    """Generate and play one chunk"""
    import edge_tts
    from playsound import playsound

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()
    try:
        communicate = edge_tts.Communicate(text, voice, rate="+10%")
        await communicate.save(tmp.name)
        if not _stop_speaking.is_set():
            playsound(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

def stop_speaking():
    """Bahar se call karke voice rokne ke liye"""
    _stop_speaking.set()

# ── LISTEN ────────────────────────────────
def listen(timeout: int = 5, phrase_limit: int = 10) -> str | None:
    """Mic se suno — automatically stops any ongoing speech"""
    stop_speaking()  # Mic sun raha hai toh voice band karo

    with sr.Microphone() as src:
        console.print("[dim yellow]🎙️  Listening...[/dim yellow]")
        recognizer.adjust_for_ambient_noise(src, duration=0.4)
        try:
            audio = recognizer.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None

    for lang in ["en-IN", "hi-IN"]:
        try:
            text = recognizer.recognize_google(audio, language=lang)
            if text:
                console.print(f"[bold green]You:[/bold green] {text}")
                return text.strip()
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            console.print(f"[red]Speech API error: {e}[/red]")
            return None

    speak("Samjha nahi, dobara bolein?", silent=True)
    return None

# ── WAKE WORD LOOP ────────────────────────
def wait_for_wake_word(callback) -> None:
    speak(f"JARVIS active. Say '{config.WAKE_WORD}' to give a command.")
    console.print(f"[dim]Wake word: say '[bold]{config.WAKE_WORD}[/bold]'[/dim]")

    while True:
        with sr.Microphone() as src:
            recognizer.adjust_for_ambient_noise(src, duration=0.3)
            try:
                audio = recognizer.listen(src, timeout=3, phrase_time_limit=4)
                text = recognizer.recognize_google(audio, language="en-IN").lower()
            except Exception:
                continue
        if config.WAKE_WORD in text:
            stop_speaking()  # Agar bol raha tha toh rokdo
            speak("Haan sir, boliye?")
            command = listen(timeout=6, phrase_limit=12)
            if command:
                callback(command)