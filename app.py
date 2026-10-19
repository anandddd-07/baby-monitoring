"""
app.py - improved dark-themed Streamlit demo of the baby monitoring system.

Run with:
    ..\venv311\Scripts\python.exe -m streamlit run app.py
"""
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import time
import cv2
import datetime
import streamlit as st
import numpy as np
import voice

from detect_file import Detect_final

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


if "event_log" not in st.session_state:
    st.session_state.event_log = []
if "chart_ear" not in st.session_state:
    st.session_state.chart_ear = []
if "chart_motion" not in st.session_state:
    st.session_state.chart_motion = []
if "prev_labels" not in st.session_state:
    st.session_state.prev_labels = {"eyes": None, "body": None, "area": None}
if "activity" not in st.session_state:
    st.session_state.activity = {"start": time.time(), "awake": 0.0, "moving": 0.0, "outside": 0.0, "alerts": 0, "last": time.time()}


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Controls")
run = st.sidebar.toggle("Start camera", value=False)
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
    preview_width = st.select_slider("Preview width", [480, 640, 720, 960], value=640)

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
    live_class = "live-pill" if run else "live-pill offline"
    st.markdown(f'<div class="{live_class}"><span class="live-dot"></span> LIVE</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- main
main_left, main_right = st.columns([2.2, 1], gap="medium")

with main_left:
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
    st.session_state.prev_labels = {"eyes": None, "body": None, "area": None}

    cap = cv2.VideoCapture(int(cam_index))

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        st.error("Could not open the camera. Close other camera apps and try again.")
    else:
        try:
            frame_number = 0
            fps_start = time.time()
            frames = 0
            last_snapshot = 0.0
            last_panel_update = 0

            while True:
                ok, frame = cap.read()
                if not ok:
                    st.error("Could not read from the camera.")
                    break

                frame = cv2.flip(frame, 1)
                if frame.shape[1] > preview_width:
                    scale = preview_width / frame.shape[1]
                    frame = cv2.resize(
                        frame,
                        (preview_width, int(frame.shape[0] * scale)),
                        interpolation=cv2.INTER_AREA,
                    )

                h, w = frame.shape[:2]
                x1, x2 = int(w * left / 100), int(w * right / 100)
                y1, y2 = int(h * top / 100), int(h * bottom / 100)
                points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]

                model.motion_threshold = motion_sensitivity
                frame = model.output(frame, points)
                box_color = (60, 60, 255) if model.label_outside == "OUTSIDE" else (80, 200, 80)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

                video_slot.image(frame, channels="BGR", use_container_width=True)

                current = {"eyes": model.label_eye, "body": model.label, "area": model.label_outside}
                previous = st.session_state.prev_labels
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
                for action in actions:
                    st.session_state.event_log.append("%s %s" % (time.strftime("%H:%M:%S"), action))
                    st.session_state.event_log = st.session_state.event_log[-30:]
                    st.session_state.activity["alerts"] += 1

                last_seen = st.session_state.activity["last"]
                now = time.time()
                dt = max(0.0, min(now - last_seen, 1.0))
                st.session_state.activity["last"] = now
                if model.label_eye == "AWAKE":
                    st.session_state.activity["awake"] += dt
                if model.label == "BODY MOVING":
                    st.session_state.activity["moving"] += dt
                if model.label_outside == "OUTSIDE":
                    st.session_state.activity["outside"] += dt
                    if snapshots and now - last_seen > 5.0:
                        folder = "alert_snapshots"
                        os.makedirs(folder, exist_ok=True)
                        image_name = os.path.join(folder, "snapshot_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
                        cv2.imwrite(image_name, frame)
                        st.session_state.event_log.append("%s Snapshot saved" % time.strftime("%H:%M:%S"))

                frames += 1
                frame_number += 1
                if frame_number % 5 == 0 or actions:
                    tone_body = "warn" if model.label == "BODY MOVING" else "good"
                    tone_eye = "warn" if model.label_eye == "AWAKE" else "good"
                    tone_area = "bad" if model.label_outside == "OUTSIDE" else "good"
                    body_confidence = int(getattr(model, "body_probability", 0.0) * 100)
                    eye_confidence = int(getattr(model, "eye_probability", 0.0) * 100)

                    status_slots["Movement"].markdown(
                        status_card("Movement", model.label, tone_body, f"Confidence: {body_confidence}%"),
                        unsafe_allow_html=True,
                    )
                    status_slots["Baby status"].markdown(
                        status_card("Baby status", model.label_eye, tone_eye, f"Confidence: {eye_confidence}%"),
                        unsafe_allow_html=True,
                    )
                    status_slots["Boundary"].markdown(
                        status_card("Boundary", model.label_outside, tone_area, "Safe-area test"),
                        unsafe_allow_html=True,
                    )

                    live_status = (
                        f"**Movement:** {model.label}\n\n"
                        f"**Eyes:** {model.label_eye}\n\n"
                        f"**Area:** {model.label_outside}\n\n"
                        f"**EAR:** {model.ear:.2f}"
                    )
                    status_live.markdown(live_status)

                    if model.label_outside == "OUTSIDE":
                        alert_slot.error("⚠️ Baby is OUTSIDE the safe area")
                    elif model.label_eye == "AWAKE":
                        alert_slot.warning("Baby is awake")
                    elif model.label == "BODY MOVING":
                        alert_slot.warning("Baby is moving")
                    else:
                        alert_slot.success("All calm")

                    event_slot.markdown("\n".join(st.session_state.event_log[-15:]) or "No important events yet.")

                    fps = frames / max(time.time() - fps_start, 0.001)
                    details = "EAR: %.2f | FPS: %.0f | Movement: %.3f" % (
                        model.ear,
                        fps,
                        getattr(model, "motion_level", 0.0),
                    )

                    chart_slot.line_chart(
                        {
                            "EAR": list(st.session_state.chart_ear),
                            "Movement": list(st.session_state.chart_motion),
                        },
                        height=185,
                        use_container_width=True,
                    )
                    summary = st.session_state.activity
                    summary_slot.markdown(
                        "**Session summary**\n\n"
                        "- Awake time: **%.0fs**\n"
                        "- Moving time: **%.0fs**\n"
                        "- Outside time: **%.0fs**\n"
                        "- Alerts recorded: **%d**\n"
                        "- Session time: **%.0fs**\n"
                        "- Movement sensitivity: **%.3f**\n"
                        "- Last status detail: %s\n"
                        % (
                            summary["awake"],
                            summary["moving"],
                            summary["outside"],
                            summary["alerts"],
                            max(time.time() - summary["start"], 0.001),
                            motion_sensitivity,
                            details,
                        )
                    )
            st.session_state.prev_labels = {
                "eyes": model.label_eye,
                "body": model.label,
                "area": model.label_outside,
            }
        finally:
            cap.release()
            voice.VOICE_ENABLED = True

st.markdown(
    """
    <div class="tip">
    <strong>Demo tips:</strong> Close other camera apps, keep one person in the frame, and stay inside the drawn area for clean calm labels.
    </div>
    """,
    unsafe_allow_html=True,
)