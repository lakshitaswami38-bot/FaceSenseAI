import os
import time
from datetime import datetime, timedelta

import cv2
from deepface import DeepFace
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    create_user,
    get_emotion_dates,
    get_emotion_frequency,
    get_recent_emotion_history,
    get_user_by_id,
    get_user_by_phone,
    init_db,
    save_emotion_history,
)


app = Flask(__name__)
app.secret_key = os.environ.get("FACE_SENSE_SECRET", "facesense-dev-secret-change-me")
init_db()

EMOTIONS = ["happy", "sad", "angry", "fear", "surprise", "neutral"]
EMOTION_EMOJI = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😡",
    "fear": "😨",
    "surprise": "😲",
    "neutral": "😐",
}


SUGGESTIONS = {
    "happy": {
        "emoji": "😊",
        "message": "Great to see you happy! Keep the positive vibe going and share it with others.",
        "activity": ["Share your happiness with a friend 💬",
        "Do something creative like drawing or dancing 🎨",
        "Play a fun game 🎮",
        "Listen to your favorite upbeat music 🎧"
    ],
        "entertainment": [
            {"label": "Fun browser games", "url": "https://poki.com/"},
            {"label": "Energetic music (YouTube)", "url": "https://www.youtube.com/results?search_query=happy+mood+songs"},
        ],
    },
    "sad": {
        "emoji": "😢",
        "message": "It's okay to feel sad sometimes 💙.Take a small break, breathe, and do something gentle for yourself.",
        "activity": ["Take a short walk 🚶‍♀️",
        "Listen to calm music 🎧",
        "Talk to someone you trust 💬",
        "Try journaling your thoughts ✍️"
    ],
        "entertainment": [
            {"label": "Calm music (YouTube)", "url": "https://www.youtube.com/results?search_query=calm+music"},
            {"label": "Simple relaxing games", "url": "https://poki.com/"},
        ],
    },
    "angry": {
        "emoji": "😡",
        "message": "Take a pause. It’s okay to feel angry, but calming your mind will help you think clearly.",

    "activity": [
        "Take deep breaths for a few minutes 🧘‍♀️",
        "Go for a short walk to cool down 🚶‍♀️",
        "Listen to calming music 🎧",
        "Try a quick distraction like a simple game 🎮"
    ],
        
        "entertainment": [
            {"label": "Meditation video (YouTube)", "url": "https://www.youtube.com/watch?v=inpok4MKVLM"},
            {"label": "Stress relief games", "url": "https://poki.com/"},
        ],
    },
    "fear": {
        "emoji": "😨",
        "message": "You’re safe right now. Let’s take it one step at a time.",
         "activity": [
        "Take slow deep breaths to calm your body 🧘‍♀️",
        "Sit in a comfortable place and relax 🛋️",
        "Listen to soothing or nature sounds 🎧",
        "Distract yourself with a light and simple activity 🎮"
    ],
        "entertainment": [
            {"label": "Calm music (YouTube)", "url": "https://www.youtube.com/results?search_query=soothing+music+for+anxiety"},
            {"label": "Light distraction games", "url": "https://www.crazygames.com/"},
        ],
    },
    "surprise": {
        "emoji": "😲",
        "message": "Surprised! Let’s help you process what just happened.",
        "activity": "Take 3 slow breaths and ask: “What changed?” “What do I need right now?”",
        "entertainment": [
            {"label": "Light comedy clips (YouTube)", "url": "https://www.youtube.com/results?search_query=light+comedy+clips"},
            {"label": "Quick trivia game", "url": "https://www.sporcle.com/"},
        ],
    },
    "neutral": {
        "emoji": "😐",
        "message": "Neutral is okay — steady and clear.",
        "activity": "Productivity boost: set a 10-minute timer and start one small task. Keep it simple.",
        "entertainment": [
            {"label": "Lo-fi focus music (YouTube)", "url": "https://www.youtube.com/results?search_query=light+music"},
            {"label": "Quick browser games", "url": "https://poki.com/"},
        ],
    },
}


def normalize_emotion(raw: str) -> str:
    if not raw:
        return "neutral"
    raw = raw.strip().lower()
    if raw in EMOTIONS:
        return raw
    aliases = {
        "anxious": "fear",
        "anxiety": "fear",
        "scared": "fear",
        "afraid": "fear",
        "mad": "angry",
        "furious": "angry",
        "upset": "sad",
        "ok": "neutral",
        "fine": "neutral",
        "meh": "neutral",
    }
    return aliases.get(raw, "neutral")


def get_suggestion(emotion: str) -> dict:
    emotion = normalize_emotion(emotion)
    suggestion = {"emotion": emotion, **SUGGESTIONS.get(emotion, SUGGESTIONS["neutral"])}
    activity = suggestion.get("activity")
    if isinstance(activity, list):
        cleaned = [str(x).strip() for x in activity if str(x).strip()]
    elif isinstance(activity, str):
        cleaned = [x.strip() for x in activity.split("\n") if x.strip()]
        if not cleaned:
            cleaned = [activity.strip()] if activity.strip() else []
    else:
        cleaned = []
    suggestion["activity"] = cleaned
    return suggestion


def analyze_text_to_emotion(text: str) -> tuple[str, dict]:
    t = (text or "").lower()
    rules = {
        "happy": ["happy", "great", "good", "awesome", "excited", "joy", "amazing", "love", "fantastic"],
        "sad": ["sad", "down", "depressed", "cry", "lonely", "tired", "hopeless", "heartbroken"],
        "angry": ["angry", "mad", "furious", "annoyed", "irritated", "hate", "rage"],
        "fear": ["fear", "scared", "afraid", "anxious", "panic", "worried", "nervous", "stress"],
        "surprise": ["surprised", "shocked", "wow", "unexpected", "sudden"],
        "neutral": ["okay", "fine", "normal", "neutral", "meh"],
    }
    scores = {k: 0 for k in rules.keys()}
    for emotion, keywords in rules.items():
        for kw in keywords:
            if kw in t:
                scores[emotion] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "neutral"
    return best, {"scores": scores}


def analyze_camera_emotion(duration_sec: float = 2.5, sample_every_n_frames: int = 6) -> dict:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Make sure no other app is using it.")

    try:
        start = time.time()
        frame_idx = 0
        per_frame = []

        while time.time() - start < duration_sec:
            ok, frame = cap.read()
            if not ok:
                continue
            frame_idx += 1
            if frame_idx % sample_every_n_frames != 0:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            analysis = DeepFace.analyze(
                rgb,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="opencv",
            )

            if isinstance(analysis, list):
                analysis = analysis[0] if analysis else {}
            emo = (analysis.get("dominant_emotion") or "neutral").lower()
            probs = analysis.get("emotion") or {}
            per_frame.append({"dominant_emotion": emo, "probabilities": probs})

        if not per_frame:
            return {"dominant_emotion": "neutral", "probabilities": {}, "frames_used": 0}

        votes = {}
        for item in per_frame:
            e = normalize_emotion(item["dominant_emotion"])
            votes[e] = votes.get(e, 0) + 1
        dominant = max(votes, key=votes.get)

        avg = {}
        for item in per_frame:
            probs = item.get("probabilities") or {}
            for k, v in probs.items():
                try:
                    avg[k] = avg.get(k, 0.0) + float(v)
                except Exception:
                    continue
        for k in list(avg.keys()):
            avg[k] = round(avg[k] / max(1, len(per_frame)), 2)

        dominant_pct = None
        for k, v in avg.items():
            if normalize_emotion(k) == dominant:
                try:
                    dominant_pct = int(round(float(v)))
                except Exception:
                    dominant_pct = None
                break

        return {"dominant_emotion": dominant, "dominant_pct": dominant_pct, "frames_used": len(per_frame)}
    finally:
        cap.release()


def set_last_result(source: str, emotion: str, meta: dict | None = None, error: str | None = None) -> None:
    normalized_emotion = normalize_emotion(emotion)
    suggestion = get_suggestion(emotion)
    payload = {
        "source": source,
        "emotion": normalized_emotion,
        "suggestion": suggestion,
        "meta": meta or {},
        "error": error,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    session["last_result"] = payload
    user_id = session.get("user_id")
    if user_id:
        try:
            save_emotion_history(
                user_id=int(user_id),
                emotion=normalized_emotion,
                suggestion=suggestion.get("message", ""),
                source=source,
            )
        except Exception:
            # History save should not interrupt emotion flow.
            pass


class _CameraState:
    def __init__(self):
        self.cap = None
        self.last_frame = None
        self.status = "Look at the camera 😊"
        self.running = False
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        )
        self.eye_cascade = cv2.CascadeClassifier(
            os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")
        )
        self.smile_cascade = cv2.CascadeClassifier(
            os.path.join(cv2.data.haarcascades, "haarcascade_smile.xml")
        )

    def start(self):
        if self.cap is not None and self.running:
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam. Make sure no other app is using it.")
        self.cap = cap
        self.running = True
        self.status = "Detecting face..."
        self.last_frame = None

    def stop(self):
        self.running = False
        if self.cap is not None:
            try:
                self.cap.release()
            finally:
                self.cap = None
        self.last_frame = None
        self.status = "Look at the camera 😊"


CAMERA = _CameraState()


@app.before_request
def require_login():
    # Old code kept for reference:
    # public_endpoints = {"login_page", "login_submit", "signup_page", "signup_submit", "static"}
    # Old code kept for reference:
    # public_endpoints = {"index", "login_page", "login_submit", "signup_page", "signup_submit", "static"}
    public_endpoints = {"index", "about_page", "login_page", "login_submit", "signup_page", "signup_submit", "static"}
    if request.endpoint in public_endpoints:
        return None

    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    return None


@app.context_processor
def inject_auth_user():
    user = None
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(int(user_id))
    return {"auth_user": user}


def _build_dashboard_payload(user_id: int) -> dict:
    freq = get_emotion_frequency(user_id)
    chart_counts = [int(freq.get(emotion, 0)) for emotion in EMOTIONS]
    has_data = any(x > 0 for x in chart_counts)

    recent_rows = get_recent_emotion_history(user_id, limit=8)
    source_label = {
        "manual": "Mood Selection",
        "text": "Text Input",
        "camera": "Camera",
    }
    recent = []
    for row in recent_rows:
        emotion = normalize_emotion(str(row["emotion"]))
        src = str(row["source"] or "unknown").lower()
        recent.append(
            {
                "emotion": emotion,
                "emoji": EMOTION_EMOJI.get(emotion, "😐"),
                "timestamp": row["timestamp"],
                "source": source_label.get(src, "Unknown"),
            }
        )

    streak_days = 0
    raw_dates = get_emotion_dates(user_id)
    day_set = set()
    for day in raw_dates:
        try:
            day_set.add(datetime.strptime(day, "%Y-%m-%d").date())
        except ValueError:
            continue
    current = datetime.now().date()
    while current in day_set:
        streak_days += 1
        current = current - timedelta(days=1)

    return {
        "chart_labels": EMOTIONS,
        "chart_counts": chart_counts,
        "has_chart_data": has_data,
        "recent_history": recent,
        "streak_days": streak_days,
    }


@app.get("/signup")
def signup_page():
    if session.get("user_id"):
        # Old code kept for reference:
        # return redirect(url_for("index"))
        return redirect(url_for("dashboard_page"))
    # Old code kept for reference:
    # return render_template("signup.html")
    return redirect(url_for("login_page", tab="signup"))


@app.post("/signup")
def signup_submit():
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    occupation = (request.form.get("occupation") or "").strip()
    password = request.form.get("password") or ""

    if not name or not phone or not occupation or not password:
        # Old code kept for reference:
        # return render_template("signup.html", error="All fields are required."), 400
        return render_template("login.html", signup_error="All fields are required.", active_tab="signup"), 400

    if len(password) < 8:
        return render_template(
        "login.html",
        signup_error="Password must be at least 8 characters long.",
        active_tab="signup"
    ), 400

    if occupation not in {"Student", "Employee", "Other"}:
        occupation = "Other"

    if get_user_by_phone(phone):
        # Old code kept for reference:
        # return render_template("signup.html", error="Phone number already registered."), 400
        return render_template("login.html", signup_error="Phone number already registered.", active_tab="signup"), 400

    user_id = create_user(
        name=name,
        phone=phone,
        occupation=occupation,
        password_hash=generate_password_hash(password),
    )
    session["user_id"] = user_id
    # Old code kept for reference:
    # return redirect(url_for("index"))
    return redirect(url_for("dashboard_page"))


@app.get("/login")
def login_page():
    if session.get("user_id"):
        # Old code kept for reference:
        # return redirect(url_for("index"))
        return redirect(url_for("dashboard_page"))
    tab = (request.args.get("tab") or "login").strip().lower()
    if tab not in {"login", "signup"}:
        tab = "login"
    return render_template("login.html", active_tab=tab)


@app.post("/login")
def login_submit():
    phone = (request.form.get("phone") or "").strip()
    password = request.form.get("password") or ""

    if not phone or not password:
        return render_template("login.html", error="Phone and password are required.", active_tab="login"), 400

    user = get_user_by_phone(phone)
    if not user or not check_password_hash(user["password"], password):
        return render_template("login.html", error="Invalid phone number or password.", active_tab="login"), 401

    session["user_id"] = int(user["id"])
    # Old code kept for reference:
    # return redirect(url_for("index"))
    return redirect(url_for("dashboard_page"))


@app.get("/logout")
def logout():
    session.clear()
    # Old code kept for reference:
    # return redirect(url_for("login_page"))
    return redirect(url_for("index"))


def _annotate_frame(frame_bgr, status_text: str):
    out = frame_bgr.copy()
    h, w = out.shape[:2]
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)

    faces = CAMERA.face_cascade.detectMultiScale(
        gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
    )
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        cv2.rectangle(out, (x, y), (x + fw, y + fh), (0, 255, 200), 2)
        cv2.putText(
            out,
            "Face detected",
            (x, max(24, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 200),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            out,
            "Hold still...",
            (x, min(h - 16, y + fh + 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        if status_text == "Detecting face...":
            status_text = "Face detected. Ready to analyze..."

    overlay_h = 56
    cv2.rectangle(out, (0, 0), (w, overlay_h), (0, 0, 0), -1)
    cv2.addWeighted(out[:overlay_h, :], 0.55, out[:overlay_h, :], 0.45, 0, out[:overlay_h, :])
    cv2.putText(
        out,
        status_text,
        (14, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return out


def _mjpeg_frames():
    CAMERA.start()
    while CAMERA.running and CAMERA.cap is not None:
        ok, frame = CAMERA.cap.read()
        if not ok:
            continue
        CAMERA.last_frame = frame
        annotated = _annotate_frame(frame, CAMERA.status)
        ok2, jpg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok2:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")


def _laplacian_variance(gray_img):
    return cv2.Laplacian(gray_img, cv2.CV_64F).var()


def _validate_frame_for_emotion(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    frame_area = float(max(1, h * w))

    faces = CAMERA.face_cascade.detectMultiScale(
        gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
    )
    if len(faces) == 0:
        return False, "Face not detected. Please look at the camera and try again.", None

    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_area_ratio = (fw * fh) / frame_area
    if face_area_ratio < 0.09:
        return False, "Please move closer to the camera.", (x, y, fw, fh)

    margin = 8
    if x <= margin or y <= margin or (x + fw) >= (w - margin) or (y + fh) >= (h - margin):
        return False, "Your face is not clearly visible. Please adjust your position or lighting.", (x, y, fw, fh)

    face_gray = gray[y : y + fh, x : x + fw]
    eyes = CAMERA.eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=5)
    if len(eyes) < 1:
        return False, "Your face is not clearly visible. Please adjust your position or lighting.", (x, y, fw, fh)

    blur_value = _laplacian_variance(face_gray)
    if blur_value < 100:
        return False, "Image is blurry. Please stay still or improve lighting.", (x, y, fw, fh)

    return True, "", (x, y, fw, fh)


@app.get("/")
def index():
    # Old code kept for reference:
    # return render_template("index.html")
    if session.get("user_id"):
        return redirect(url_for("dashboard_page"))
    return render_template("index.html")


@app.get("/about")
def about_page():
    return render_template("about.html")


@app.get("/dashboard")
def dashboard_page():
    user_id = int(session.get("user_id"))
    payload = _build_dashboard_payload(user_id)
    return render_template("dashboard.html", dashboard=payload)


@app.get("/select")
def select_page():
    return render_template("select.html")


@app.post("/select")
def select_submit():
    data = request.get_json(silent=True) or request.form
    emotion = data.get("emotion", "neutral")
    set_last_result("manual", emotion, meta={})
    return jsonify({"ok": True, "redirect": url_for("result_page")})


@app.get("/text")
def text_page():
    return render_template("text.html")


@app.post("/text")
def text_submit():
    data = request.get_json(silent=True) or request.form
    text = data.get("text", "")
    emotion, meta = analyze_text_to_emotion(text)
    meta["text"] = text
    set_last_result("text", emotion, meta=meta)
    return jsonify({"ok": True, "redirect": url_for("result_page")})


@app.get("/camera")
def camera_page():
    return render_template("camera.html")


@app.get("/video_feed")
def video_feed():
    return Response(_mjpeg_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.post("/camera/start")
def camera_start():
    try:
        CAMERA.start()
        CAMERA.status = "Detecting face..."
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/camera")
def camera_analyze():
    try:
        CAMERA.start()
        CAMERA.status = "Analyzing your expression..."

        start = time.time()
        frame_idx = 0
        per_frame = []
        duration_sec = 2.5
        sample_every_n_frames = 6
        validation_error = None

        while time.time() - start < duration_sec:
            frame = CAMERA.last_frame
            if frame is None:
                time.sleep(0.02)
                continue

            frame_idx += 1
            if frame_idx % sample_every_n_frames != 0:
                time.sleep(0.01)
                continue

            valid, err_msg, _ = _validate_frame_for_emotion(frame)
            if not valid:
                validation_error = err_msg
                CAMERA.status = err_msg
                time.sleep(0.04)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            analysis = DeepFace.analyze(
                rgb,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="opencv",
            )
            if isinstance(analysis, list):
                analysis = analysis[0] if analysis else {}
            emo = (analysis.get("dominant_emotion") or "neutral").lower()
            probs = analysis.get("emotion") or {}
            per_frame.append({"dominant_emotion": emo, "probabilities": probs})
            time.sleep(0.02)

        if not per_frame:
            msg = validation_error or "Face not detected. Please look at the camera and try again."
            CAMERA.stop()
            set_last_result("camera", "neutral", meta={}, error=msg)
            return jsonify({"ok": False, "redirect": url_for("result_page"), "error": msg}), 400
        else:
            votes = {}
            for item in per_frame:
                e = normalize_emotion(item["dominant_emotion"])
                votes[e] = votes.get(e, 0) + 1
            dominant = max(votes, key=votes.get)

            avg = {}
            for item in per_frame:
                probs = item.get("probabilities") or {}
                for k, v in probs.items():
                    try:
                        avg[k] = avg.get(k, 0.0) + float(v)
                    except Exception:
                        continue
            for k in list(avg.keys()):
                avg[k] = avg[k] / max(1, len(per_frame))

            dominant_pct = None
            for k, v in avg.items():
                if normalize_emotion(k) == dominant:
                    try:
                        dominant_pct = int(round(float(v)))
                    except Exception:
                        dominant_pct = None
                    break

            res = {"dominant_emotion": dominant, "dominant_pct": dominant_pct, "frames_used": len(per_frame)}

        emotion = res.get("dominant_emotion", "neutral")
        set_last_result("camera", emotion, meta=res)
        CAMERA.stop()
        return jsonify({"ok": True, "redirect": url_for("result_page"), "emotion": emotion})
    except Exception as e:
        try:
            CAMERA.stop()
        except Exception:
            pass
        set_last_result("camera", "neutral", meta={}, error=str(e))
        return jsonify({"ok": False, "redirect": url_for("result_page"), "error": str(e)}), 500


@app.get("/result")
def result_page():
    last = session.get("last_result")
    if not last:
        return redirect(url_for("index"))
    return render_template("result.html", result=last)


if __name__ == "__main__":
    app.run(debug=True)
