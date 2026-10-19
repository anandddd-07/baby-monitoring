import os
import sys
import threading
import time
import webbrowser

import detect_file
import motion
import voice
import streamlit.web.cli as stcli


def _open_browser_when_ready(url, attempts=60):
    """Wait for the Streamlit server, then open the default browser."""

    def worker():
        import urllib.request

        for _ in range(attempts):
            try:
                urllib.request.urlopen(url, timeout=1)
                webbrowser.open(url)
                return
            except Exception:
                time.sleep(1)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def main():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_path, "app.py")
    port = os.environ.get("BABY_MONITOR_PORT", "8501")
    url = "http://localhost:%s" % port

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port",
        port,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
    ]

    _open_browser_when_ready(url)
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
