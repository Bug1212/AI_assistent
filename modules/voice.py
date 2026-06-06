# ─────────────────────────────────────────
# JARVIS V2 — VOICE MODULE
# ─────────────────────────────────────────
import pyttsx3
import speech_recognition as sr
from rich.console import Console
import config

console = Console()
recognizer = sr.Recognizer()

# TTS Engine init
engine = pyttsx3.init()
engine.setProperty('rate', config.VOICE_RATE)
engine.setProperty('volume', config.VOICE_VOLUME)

# Try to set a good voice (prefer female/Indian English if available)
def _set_best_voice():
    voices = engine.getProperty('voices')
    preferred = None
    for v in voices:
        name = v.name.lower()
        if any(k in name for k in ["zira", "heera", "ravi", "indian", "en_in"]):
            preferred = v.id
            break
    if not preferred and voices:
        preferred = voices[0].id
    if preferred:
        engine.setProperty('voice', preferred)

_set_best_voice()

# ── SPEAK ─────────────────────────────────
def speak(text: str, silent: bool = False):
    """JARVIS bolega — text ko voice mein convert karega"""
    console.print(f"[bold cyan]JARVIS:[/bold cyan] {text}")
    if not silent:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            console.print(f"[dim red]Voice error: {e}[/dim red]")

# ── LISTEN (single shot) ──────────────────
def listen(timeout: int = 5, phrase_limit: int = 10) -> str | None:
    """Mic se ek baar suno — string return karo ya None"""
    with sr.Microphone() as src:
        console.print("[dim yellow]🎙️  Listening...[/dim yellow]")
        recognizer.adjust_for_ambient_noise(src, duration=0.5)
        try:
            audio = recognizer.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None

    try:
        text = recognizer.recognize_google(audio, language="en-IN")
        console.print(f"[bold green]You:[/bold green] {text}")
        return text.strip()
    except sr.UnknownValueError:
        speak("Sorry, samjha nahi. Dobara bolein?", silent=True)
        console.print("[dim]Could not understand audio.[/dim]")
        return None
    except sr.RequestError as e:
        console.print(f"[red]Speech API error: {e}[/red]")
        return None

# ── WAKE WORD LOOP ────────────────────────
def wait_for_wake_word(callback) -> None:
    """
    Background mein chalta hai — 'Hey JARVIS' sunne pe callback(command) call karta hai.
    callback: function jo user command leti hai (str)
    """
    speak("JARVIS V2 active. Say 'Hey JARVIS' to give a command.", silent=True)
    console.print(f"[dim]Wake word mode: say '[bold]{config.WAKE_WORD}[/bold]' to activate.[/dim]")

    while True:
        with sr.Microphone() as src:
            recognizer.adjust_for_ambient_noise(src, duration=0.3)
            try:
                audio = recognizer.listen(src, timeout=3, phrase_time_limit=4)
                text = recognizer.recognize_google(audio, language="en-IN").lower()
            except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
                continue

        if config.WAKE_WORD in text:
            speak("Haan sir, boliye?")
            command = listen(timeout=6, phrase_limit=12)
            if command:
                callback(command)
