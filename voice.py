"""
voice.py - alerts for the baby monitor.

Put your own audio files in a folder called "audio" next to this file:
    audio/wakeup.wav    (baby is awake)
    audio/outside.wav   (baby is outside the safe area)
    audio/moving.wav    (baby is moving)
    audio/calm.wav      (all is calm)
.wav files work on Windows with nothing to install.
.mp3 / .ogg files also work if you run:  pip install pygame

If a file is missing, the built-in Windows voice speaks the alert instead.
Set VOICE_ENABLED = False to mute everything (messages are still printed).
"""
import os
import subprocess
import sys
import threading

VOICE_ENABLED = True


def _base_dir():
    """Folder that holds the project files, also works inside a packaged app."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


AUDIO_DIR = os.path.join(_base_dir(), "audio")
EXTENSIONS = ("wav", "mp3", "ogg")

_lock = threading.Lock()


def _find_audio(name):
    for ext in EXTENSIONS:
        path = os.path.join(AUDIO_DIR, "%s.%s" % (name, ext))
        if os.path.isfile(path):
            return path
    return None


def _play_file(path):
    """Play an audio file and wait until it finishes. Returns True on success."""
    try:
        if path.lower().endswith(".wav") and sys.platform == "win32":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
            return True

        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        return True
    except Exception as error:
        print("Could not play", path, "->", error)
        return False


def _speak(text):
    """Built-in Windows speech, used when there is no audio file."""
    if sys.platform != "win32":
        return
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('%s')" % text
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=20,
        )
    except Exception as error:
        print("Could not speak the alert:", error)


def _alert(name, text):
    print("Voice alert:", text)
    if not VOICE_ENABLED:
        return

    # If something is already playing, skip this alert instead of stacking sounds
    if not _lock.acquire(blocking=False):
        return
    try:
        path = _find_audio(name)
        if path and _play_file(path):
            return
        if not path:
            print("(no audio file for '%s' in the audio folder, using the built-in voice)" % name)
        _speak(text)
    finally:
        _lock.release()


def voice_Alert_Wakeup():
    _alert("wakeup", "Warning. The baby is awake.")


def voice_Alert_Outside():
    _alert("outside", "Warning. The baby is outside the safe area.")


def voice_Alert_Moving():
    _alert("moving", "Warning. The baby is moving.")


def voice_Alert_Calm():
    _alert("calm", "All is calm. The baby is sleeping peacefully.")