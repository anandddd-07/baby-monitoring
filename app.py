"""
app.py - improved dark-themed Streamlit demo of the baby monitoring system.

Run with:
    ..\venv311\Scripts\python.exe -m streamlit run app.py
"""
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import time
import threading
import cv2
import datetime
import streamlit as st
import numpy as np
import voice

from detect_file import Detect_final
from stream_server import MjpegServer

st.set_page_config(
    page_title="Baby Monitoring System",
    page_icon="baby",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --card: #132038;
        --light: #8dd3ff;
        --green: #34d399;
        --blue: #60a5fa;
        --amber: #fbbf24;
        --red: #fb7185;
    }
    .stApp {
        background: linear-gradient(180deg, #04070f 0%, #0b1222 100%);
        color: #f8fbff;
    }
    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0.4rem;
    }
    .header {
        font-size: 2rem;
        font-weight: 900;
        margin: 0;
        line-height: 1;
    }
    .subtitle {
        color: var(--light);
        font-size: 0.85rem;
        letter-spacing: 0.12em;
        margin-top: 0.25rem;
    }
    .card {
        background: rgba(20, 34, 60, 0.95);
        border: 1px solid rgba(96, 165, 250, 0.15);
        border-radius: 16px;
        padding: 0.8rem;
        margin-bottom: 0.55rem;
        min-height: 118px;
    }
    .card-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9fb4d6;
        margin-bottom: 0.3rem;
    }
    .card-value {
        font-size: 1.35rem;
        font-weight: 850;
        margin: 0;
    }
    .good { color: var(--green); }
    .warn { color: var(--amber); }
    .bad { color: var(--red); }
    .video-box {
        background: rgba(24, 35, 58, 0.96);
        border: 1px solid rgba(96, 165, 250, 0.15);
        border-radius: 18px;
        padding: 0.9rem;
        margin-top: 1rem;
    }
    .tip {
        color: #bbd0eb;
        font-size: 0.82rem;
        line-height: 1.45;
    }
    .public-banner {
        margin: 0.45rem 0 0.2rem 0;
        padding: 0.5rem 0.9rem;
        border-radius: 12px;
        border: 1px solid rgba(52, 211, 153, 0.45);
        background: rgba(52, 211, 153, 0.10);
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.85rem;
    }
    .public-dot {
        width: 9px; height: 9px; border-radius: 50%;
        background: #34d399; display: inline-block;
    }
    .public-label {
        color: #86efac; font-weight: 800;
        letter-spacing: 0.12em; font-size: 0.72rem;
    }
    .public-url {
        color: #f8fbff; font-family: Consolas, Menlo, monospace;
        font-size: 0.85rem; overflow-wrap: anywhere;
    }
    /* Bigger "Start camera" switch, placed in the middle of the page. */
    .st-key-start_camera {
        display: flex;
        justify-content: center;
        margin: 0.15rem 0 0.35rem 0;
    }
    .st-key-start_camera [data-testid="stCheckbox"] label {
        background: rgba(20, 34, 60, 0.95);
        border: 1px solid rgba(96, 165, 250, 0.30);
        border-radius: 999px;
        padding: 0.65rem 1.4rem 0.65rem 1.1rem;
        gap: 0.9rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .st-key-start_camera [data-testid="stCheckbox"] label:hover {
        border-color: rgba(52, 211, 153, 0.55);
    }
    .st-key-start_camera [data-testid="stWidgetLabel"] p {
        font-size: 1.35rem;
        font-weight: 800;
        color: #f8fbff;
        letter-spacing: 0.02em;
    }
    .st-key-start_camera [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] {
        visibility: visible;
    }
    /* Make the switch itself larger. */
    .st-key-start_camera [data-testid="stCheckbox"] label > div:nth-of-type(1) {
        transform: scale(1.35);
        transform-origin: left center;
        margin-right: 0.45rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_model():
    return Detect_final()


def tone(value, category):
    if category == "body":
        return "warn" if value == "BODY MOVING" else "good"
    if category == "eye":
        return "warn" if value == "AWAKE" else "good"
    if category == "area":
        return "bad" if value == "OUTSIDE" else "good"
    return "good"


def status_card(label, value, tone_name, extra=""):
    return f"""
    <div class="card">
        <div class="card-label">{label}</div>
        <p class="card-value {tone_name}">{value}</p>
        <div class="tip">{extra}</div>
    </div>
    """


def encode_jpeg(frame, quality):
    """Encode a BGR frame as JPEG bytes.

    A PNG frame is roughly 5-10x larger than a JPEG, and every byte has to
    travel through the tunnel to a remote browser. JPEG keeps the video
    responsive when the app is used as a public website.
    """
    ok, buffer = cv2.imencode(
        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    )
    if not ok:
        return None
    return buffer.tobytes()


if "event_log" not in st.session_state:
    st.session_state.event_log = []

# The "Start camera" switch is rendered in the main area, but the header
# needs to know its value, so the state is tracked here.
if "start_camera" not in st.session_state:
    st.session_state.start_camera = False


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Controls")
cam_index = st.sidebar.number_input("Camera number", 0, 5, 0, 1)

st.sidebar.subheader("Safe area")
left = st.sidebar.slider("Left edge", 0, 100, 10)
right = st.sidebar.slider("Right edge", 0, 100, 90)
top = st.sidebar.slider("Top edge", 0, 100, 10)
bottom = st.sidebar.slider("Bottom edge", 0, 100, 90)

with st.sidebar.expander("Alerts and detection"):
    voice_enabled = st.toggle("Voice alerts", value=True)
    motion_sensitivity = st.slider("Movement sensitivity", 0.005, 0.150, 0.030, 0.005)
    snapshots = st.toggle("Save snapshots on alerts", value=False)
    large_text = st.toggle("Large text mode", value=False)

with st.sidebar.expander("Video streaming"):
    # Public tunnels have limited bandwidth, so let the user trade quality for speed.
    # Locally we can afford full quality, over a tunnel we need to cut the bytes.
    is_public = bool(os.environ.get("BABY_MONITOR_PUBLIC_URL", "").strip())
    default_index = 2 if is_public else 0
    stream_quality = st.selectbox(
        "Quality",
        ["Smooth (local)", "Balanced", "Fast (public)"],
        index=default_index,
    )
    if stream_quality == "Smooth (local)":
        preview_width, jpeg_quality = 960, 88
    elif stream_quality == "Balanced":
        preview_width, jpeg_quality = 640, 75
    else:
        preview_width, jpeg_quality = 480, 55

    st.caption(
        "Lower quality sends fewer bytes, which keeps the video smooth when "
        "viewed through a public tunnel."
    )

if large_text:
    st.markdown(
        "<style>h1,p,li,label,button{font-size:1.1em !important;}</style>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    '<div class="tip">Close camera apps first. Keep one person visible. Keep lighting steady.</div>',
    unsafe_allow_html=True,
)

voice.VOICE_ENABLED = voice_enabled


# ---------------------------------------------------------------- header
head_left, head_right = st.columns([6, 1])
with head_left:
    st.markdown("<div class='header'>Baby Monitoring System</div>", unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Real-Time Baby Monitoring</div>', unsafe_allow_html=True)
with head_right:
    live_class = "live-pill" if st.session_state.start_camera else "live-pill offline"
    st.markdown(f'<div class="{live_class}"><span class="live-dot"></span> LIVE</div>', unsafe_allow_html=True)

# Show the public address when the app is running behind a tunnel.
public_url = os.environ.get("BABY_MONITOR_PUBLIC_URL", "").strip()
if public_url:
    st.markdown(
        """
        <div class="public-banner">
            <span class="public-dot"></span>
            <span class="public-label">PUBLIC WEBSITE</span>
            <span class="public-url">%s</span>
        </div>
        """
        % public_url.replace("&", "&amp;"),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- main
main_left, main_right = st.columns([2.2, 1], gap="medium")

with main_left:
    # The Start camera switch sits in the middle of the page and is made
    # bigger with CSS, so it is easy to find and click during a demo.
    run = st.toggle(
        "Start camera",
        key="start_camera",
        on_change=lambda: None,
    )
    alert_slot = st.empty()
    st.markdown('<div class="camera-title">LIVE WEBCAM FEED</div>', unsafe_allow_html=True)
    video_slot = st.empty()

with main_right:
    status_slots = {
        "Movement": st.empty(),
        "Baby status": st.empty(),
        "Boundary": st.empty(),
    }
    tabs = st.tabs(["Status", "Event log", "Charts", "Summary"])
    status_live = tabs[0].empty()
    event_slot = tabs[1].empty()
    chart_slot = tabs[2].empty()
    summary_slot = tabs[3].empty()

if not run:
    video_slot.info("Turn on Start camera in the sidebar to begin.")
    status_slots["Movement"].markdown(status_card("Movement", "NO MOVING", "good"), unsafe_allow_html=True)
    status_slots["Baby status"].markdown(status_card("Baby status", "SLEEPING", "good"), unsafe_allow_html=True)
    status_slots["Boundary"].markdown(status_card("Boundary", "INSIDE", "good"), unsafe_allow_html=True)
    status_live.markdown("**Status:** Nothing is running yet.")
    event_slot.markdown("No important events yet.")
    summary_slot.markdown("**Session has not started.**")
    chart_slot.markdown("Charts will appear here after the camera starts.")
elif left >= right or top >= bottom:
    st.sidebar.error("Left must be smaller than Right, and Top smaller than Bottom.")
else:
    model = load_model()
    model.reset()

    # The detection runs in its own thread and publishes frames to the small
    # MJPEG server. The browser then gets one long-lived connection instead of
    # a separate download for every frame, which is what made it choppy.
    if "mjpeg_server" not in st.session_state:
        server = MjpegServer(port=8765)
        if server.start():
            st.session_state.mjpeg_server = server
        else:
            st.session_state.mjpeg_server = None
    server = st.session_state.get("mjpeg_server")

    if server is not None:
        video_slot.markdown(
            '<img src="%s" style="width:100%%;border-radius:14px;'
            'border:1px solid rgba(96,165,250,0.15);" />' % server.url,
            unsafe_allow_html=True,
        )
    else:
        video_slot.info("Video stream server unavailable, using slow fallback.")

    # Streamlit re-runs this script whenever a widget changes, so the worker
    # is created only once and kept in session state. Otherwise every re-run
    # would start another thread and they would fight over the camera.
    if "worker_state" not in st.session_state:
        st.session_state.worker_state = {
            "lock": threading.Lock(),
            "labels": {"eyes": "Waiting", "body": "Waiting", "area": "Waiting"},
            "ear": 0.0,
            "body_conf": 0.0,
            "eye_conf": 0.0,
            "motion": 0.0,
            "fps": 0.0,
            "chart_ear": [],
            "chart_motion": [],
            "events": [],
            "alerts": 0,
            "awake": 0.0,
            "moving": 0.0,
            "outside": 0.0,
            "started": time.time(),
            "last": time.time(),
            "stop": False,
            "config": {},
            "error": None,
            "thread": None,
        }
    state = st.session_state.worker_state

    # Push the current settings into the worker. The worker reads these each
    # frame, so changing a slider takes effect immediately.
    state["config"] = {
        "model": model,
        "cam_index": int(cam_index),
        "area": (left, right, top, bottom),
        "sensitivity": motion_sensitivity,
        "quality": jpeg_quality,
        "width": preview_width,
        "snapshots": snapshots,
        "server": server,
    }

    def worker():
        """Read the camera, run detection, publish frames."""
        cap = None
        opened_index = None
        detector = None
        frames = 0
        fps_start = time.time()
        previous = {"eyes": None, "body": None, "area": None}
        last_snapshot = 0.0
        chart_ear = []
        chart_motion = []

        try:
            while not state["stop"]:
                config = state["config"]
                detector = config["model"]
                cam_index = config["cam_index"]

                # Reopen the camera if the user picked a different one.
                if cap is None or opened_index != cam_index:
                    if cap is not None:
                        cap.release()
                        cap = None
                    cap = cv2.VideoCapture(cam_index)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not cap.isOpened():
                        state["error"] = "Could not open the camera."
                        time.sleep(0.5)
                        continue
                    opened_index = cam_index
                    detector.reset()
                    previous = {"eyes": None, "body": None, "area": None}
                    frames = 0
                    fps_start = time.time()

                ok, frame = cap.read()
                if not ok:
                    state["error"] = "Could not read from the camera."
                    time.sleep(0.3)
                    continue

                state["error"] = None
                frame = cv2.flip(frame, 1)
                target_width = config["width"]
                if frame.shape[1] > target_width:
                    scale = target_width / frame.shape[1]
                    frame = cv2.resize(
                        frame,
                        (target_width, int(frame.shape[0] * scale)),
                        interpolation=cv2.INTER_AREA,
                    )

                l, r, t, b = config["area"]
                h, w = frame.shape[:2]
                x1, x2 = int(w * l / 100), int(w * r / 100)
                y1, y2 = int(h * t / 100), int(h * b / 100)
                points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]

                detector.motion_threshold = config["sensitivity"]
                frame = detector.output(frame, points)
                box_color = (60, 60, 255) if detector.label_outside == "OUTSIDE" else (80, 200, 80)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

                jpeg = encode_jpeg(frame, config["quality"])
                if jpeg is not None and config["server"] is not None:
                    config["server"].update(jpeg)

                current = {
                    "eyes": detector.label_eye,
                    "body": detector.label,
                    "area": detector.label_outside,
                }

                chart_ear.append(detector.ear)
                chart_motion.append(float(getattr(detector, "body_probability", 0.0)))
                chart_ear = chart_ear[-60:]
                chart_motion = chart_motion[-60:]

                actions = []
                if previous["eyes"] is not None and previous["eyes"] != current["eyes"]:
                    if current["eyes"] == "AWAKE":
                        actions.append("Baby is AWAKE")
                if previous["body"] is not None and previous["body"] != current["body"]:
                    if current["body"] == "BODY MOVING":
                        actions.append("Body movement detected")
                if previous["area"] is not None and previous["area"] != current["area"]:
                    if current["area"] == "OUTSIDE":
                        actions.append("Baby is OUTSIDE the safe area")
                previous = current

                now = time.time()
                dt = max(0.0, min(now - state["last"], 1.0))
                state["last"] = now

                frames += 1
                fps = frames / max(now - fps_start, 0.001)

                with state["lock"]:
                    state["labels"] = current
                    state["ear"] = detector.ear
                    state["body_conf"] = float(getattr(detector, "body_probability", 0.0))
                    state["eye_conf"] = float(getattr(detector, "eye_probability", 0.0))
                    state["motion"] = float(getattr(detector, "motion_level", 0.0))
                    state["fps"] = fps
                    state["chart_ear"] = list(chart_ear)
                    state["chart_motion"] = list(chart_motion)
                    if current["eyes"] == "AWAKE":
                        state["awake"] += dt
                    if current["body"] == "BODY MOVING":
                        state["moving"] += dt
                    if current["area"] == "OUTSIDE":
                        state["outside"] += dt
                    for action in actions:
                        state["events"].append(
                            "%s %s" % (time.strftime("%H:%M:%S"), action)
                        )
                        state["events"] = state["events"][-30:]
                        state["alerts"] += 1

                if config["snapshots"] and current["area"] == "OUTSIDE" and now - last_snapshot > 5.0:
                    last_snapshot = now
                    folder = "alert_snapshots"
                    os.makedirs(folder, exist_ok=True)
                    name = os.path.join(folder, "snapshot_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
                    cv2.imwrite(name, frame)

                time.sleep(0.001)
        finally:
            if cap is not None:
                cap.release()

    if state.get("thread") is None or not state["thread"].is_alive():
        state["stop"] = False
        state["thread"] = threading.Thread(target=worker, daemon=True)
        state["thread"].start()

    # The UI thread only refreshes the text panels, never the video itself.
    last_ui = 0.0
    while True:
        if state.get("error"):
            st.error(state["error"])
            time.sleep(0.5)
            continue

        now = time.time()
        if now - last_ui >= 0.25:
            last_ui = now
            with state["lock"]:
                labels = dict(state["labels"])
                ear = state["ear"]
                body_conf = int(state["body_conf"] * 100)
                eye_conf = int(state["eye_conf"] * 100)
                motion = state["motion"]
                fps = state["fps"]
                events = list(state["events"])
                alerts = state["alerts"]
                awake = state["awake"]
                moving = state["moving"]
                outside = state["outside"]
                chart_ear = list(state.get("chart_ear", []))
                chart_motion = list(state.get("chart_motion", []))

            tone_body = "warn" if labels["body"] == "BODY MOVING" else "good"
            tone_eye = "warn" if labels["eyes"] == "AWAKE" else "good"
            tone_area = "bad" if labels["area"] == "OUTSIDE" else "good"

            status_slots["Movement"].markdown(
                status_card("Movement", labels["body"], tone_body, f"Confidence: {body_conf}%"),
                unsafe_allow_html=True,
            )
            status_slots["Baby status"].markdown(
                status_card("Baby status", labels["eyes"], tone_eye, f"Confidence: {eye_conf}%"),
                unsafe_allow_html=True,
            )
            status_slots["Boundary"].markdown(
                status_card("Boundary", labels["area"], tone_area, "Safe-area test"),
                unsafe_allow_html=True,
            )

            status_live.markdown(
                f"**Movement:** {labels['body']}\n\n"
                f"**Eyes:** {labels['eyes']}\n\n"
                f"**Area:** {labels['area']}\n\n"
                f"**EAR:** {ear:.2f}"
            )

            if labels["area"] == "OUTSIDE":
                alert_slot.error("⚠️ Baby is OUTSIDE the safe area")
            elif labels["eyes"] == "AWAKE":
                alert_slot.warning("Baby is awake")
            elif labels["body"] == "BODY MOVING":
                alert_slot.warning("Baby is moving")
            else:
                alert_slot.success("All calm")

            event_slot.markdown("\n".join(events[-15:]) or "No important events yet.")

            if len(chart_ear) > 1:
                chart_slot.line_chart(
                    {"EAR": chart_ear, "Movement": chart_motion},
                    height=185,
                    width="stretch",
                )

            details = "EAR: %.2f | FPS: %.0f | Movement: %.3f" % (ear, fps, motion)
            summary_slot.markdown(
                "**Session summary**\n\n"
                "- Awake time: **%.0fs**\n"
                "- Moving time: **%.0fs**\n"
                "- Outside time: **%.0fs**\n"
                "- Alerts recorded: **%d**\n"
                "- Session time: **%.0fs**\n"
                "- Movement sensitivity: **%.3f**\n"
                "- Stream quality: **%s**\n"
                "- Last status detail: %s\n"
                % (
                    awake,
                    moving,
                    outside,
                    alerts,
                    max(time.time() - state["started"], 0.001),
                    motion_sensitivity,
                    stream_quality,
                    details,
                )
            )

        time.sleep(0.05)

st.markdown(
    """
    <div class="tip">
    <strong>Demo tips:</strong> Close other camera apps, keep one person in the frame, and stay inside the drawn area for clean calm labels.
    </div>
    """,
    unsafe_allow_html=True,
)