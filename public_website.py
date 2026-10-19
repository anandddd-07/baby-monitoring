"""
public_website.py - starts the Baby Monitoring System as a PUBLIC website.

It does three things:
  1. starts the Streamlit app on port 8501
  2. starts a Cloudflare Tunnel so the app gets a public https:// address
  3. opens that public address in your default browser

Run it:
    venv311\\Scripts\\python.exe public_website.py

Keep this window open while sharing - closing it stops the public website.
"""
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = "8501"
CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_cloudflared():
    """Find the cloudflared executable."""
    candidates = [
        CLOUDFLARED,
        r"C:\Program Files\cloudflared\cloudflared.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     r"Microsoft\WinGet\Links\cloudflared.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    found = shutil_which("cloudflared")
    return found


def shutil_which(name):
    from shutil import which

    return which(name)


def wait_for_app(timeout=90):
    """Wait until the local app answers."""
    url = "http://localhost:%s/_stcore/health" % PORT
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def start_app(public_url=None):
    python = os.path.join(HERE, "venv311", "Scripts", "python.exe")
    if not os.path.isfile(python):
        python = sys.executable
    env = os.environ.copy()
    if public_url:
        env["BABY_MONITOR_PUBLIC_URL"] = public_url
    return subprocess.Popen(
        [
            python, "-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", PORT,
            "--browser.gatherUsageStats", "false",
        ],
        cwd=HERE,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_tunnel(exe, on_url):
    """Start cloudflared and call on_url with the public address."""
    process = subprocess.Popen(
        [exe, "tunnel", "--url", "http://localhost:%s" % PORT, "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def reader():
        for line in process.stdout:
            match = URL_RE.search(line)
            if match:
                on_url(match.group(0))

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    return process


def main():
    def say(text=""):
        print(text, flush=True)

    say("=" * 60)
    say("  Baby Monitoring System - PUBLIC WEBSITE")
    say("=" * 60)
    say()

    exe = find_cloudflared()
    if not exe:
        say("cloudflared was not found.")
        say("Install it with:  winget install --id Cloudflare.cloudflared")
        say()
        say("Starting the app locally only ...")
        app = start_app()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            app.terminate()
        return 1

    # Start the tunnel first so the app can display its own public address.
    say("1. Creating the public URL ...")
    url_box = {}
    url_ready = threading.Event()

    def grab_url(url):
        url_box["url"] = url
        url_ready.set()

    tunnel = start_tunnel(exe, grab_url)

    if not url_ready.wait(timeout=60):
        say("   The tunnel did not start in time.")
        tunnel.terminate()
        return 1

    public_url = url_box["url"]
    say("   Public URL: %s" % public_url)
    say()

    say("2. Starting the app on port %s ..." % PORT)
    app = start_app(public_url=public_url)

    if not wait_for_app():
        say("   The app did not start. Check the console for errors.")
        app.terminate()
        tunnel.terminate()
        return 1

    say("   App is running.")
    say()
    say("=" * 60)
    say("  YOUR PUBLIC WEBSITE IS LIVE")
    say("=" * 60)
    say()
    say("   %s" % public_url)
    say()
    say("   Opening it in your browser now.")
    say("   Share this link with anyone - they can watch the demo.")
    say()
    say("   Keep this window OPEN while sharing.")
    say("   Press Ctrl+C to stop the public website.")
    say()
    try:
        webbrowser.open(public_url)
    except Exception:
        pass

    try:
        while True:
            if tunnel.poll() is not None:
                say("The tunnel stopped unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        say()
        say("Stopping ...")
    finally:
        for process in (tunnel, app):
            try:
                process.terminate()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
