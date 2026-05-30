import os
import io
import re
import json
import time
import uuid
import tempfile
import threading
import subprocess

from faster_whisper import WhisperModel
from flask import Flask, render_template, request, send_file, jsonify, Response, stream_with_context

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

_model = None
_model_name = None
_model_lock = threading.Lock()
jobs = {}

ALLOWED_EXTENSIONS = {
    "mp4", "mkv", "mov", "avi", "webm",
    "mp3", "wav", "m4a", "ogg", "flac", "aac",
}


def get_model(name):
    global _model, _model_name
    with _model_lock:
        if _model is None or _model_name != name:
            _model = WhisperModel(name, device="cpu", compute_type="int8")
            _model_name = name
    return _model


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_audio_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0


def seconds_to_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_time(time_str):
    time_str = time_str.strip()
    patterns = [
        r"^(\d+):(\d+):(\d+)[,.](\d+)$",
        r"^(\d+):(\d+):(\d+)$",
        r"^(\d+):(\d+)$",
        r"^(\d+\.?\d*)$",
    ]
    for i, pattern in enumerate(patterns):
        m = re.match(pattern, time_str)
        if m:
            g = m.groups()
            if i == 0:
                return int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
            elif i == 1:
                return int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])
            elif i == 2:
                return int(g[0]) * 60 + int(g[1])
            elif i == 3:
                return float(g[0])
    raise ValueError(f"Format waktu tidak valid: {time_str}")


def generate_srt(subtitles):
    lines = []
    for idx, sub in enumerate(subtitles, start=1):
        start = seconds_to_srt_time(sub["start"])
        end = seconds_to_srt_time(sub["end"])
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(sub["text"])
        lines.append("")
    return "\n".join(lines)


def run_transcribe(job_id, tmp_path, model_size, language, prompt, beam_size):
    def update(progress=None, message=None, **kwargs):
        if progress is not None:
            jobs[job_id]["progress"] = progress
        if message is not None:
            jobs[job_id]["message"] = message
        jobs[job_id].update(kwargs)

    try:
        update(2, "Mengukur durasi audio...")
        duration = get_audio_duration(tmp_path)
        dur_label = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "?"

        update(5, f"Memuat model {model_size}... (pertama kali bisa beberapa menit)")
        model = get_model(model_size)

        update(10, f"Transkripsi dimulai — audio {dur_label}")

        segments_gen, info = model.transcribe(
            tmp_path,
            language=language or None,
            initial_prompt=prompt or None,
            beam_size=beam_size,
            best_of=beam_size,
            temperature=0,
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        total_dur = info.duration if info.duration else duration
        detected_lang = info.language
        segments = []

        for seg in segments_gen:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })
            pct = min(95, int((seg.end / total_dur) * 85) + 10) if total_dur > 0 else 50
            elapsed = f"{seg.end:.0f}s / {total_dur:.0f}s"
            update(pct, f"Memproses {elapsed}... ({len(segments)} segmen)")

        update(
            progress=100,
            message=f"Selesai — {len(segments)} segmen (bahasa: {detected_lang})",
            status="done",
            result=segments,
            language=detected_lang,
        )

    except Exception as e:
        jobs[job_id].update({"status": "error", "message": str(e)})
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    subtitles = data.get("subtitles", [])
    filename = data.get("filename", "subtitle").strip() or "subtitle"
    if not filename.endswith(".srt"):
        filename += ".srt"

    errors, parsed = [], []
    for i, sub in enumerate(subtitles):
        try:
            start = parse_time(sub.get("start", "0"))
            end = parse_time(sub.get("end", "0"))
            text = sub.get("text", "").strip()
            if not text:
                errors.append(f"Baris {i+1}: teks tidak boleh kosong")
                continue
            if end <= start:
                errors.append(f"Baris {i+1}: waktu akhir harus lebih besar dari waktu awal")
                continue
            parsed.append({"start": start, "end": end, "text": text})
        except ValueError as e:
            errors.append(str(e))

    if errors:
        return jsonify({"error": "\n".join(errors)}), 400

    buf = io.BytesIO(generate_srt(parsed).encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="text/plain", as_attachment=True, download_name=filename)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang dikirim."}), 400

    f = request.files["file"]
    if not f.filename or not allowed(f.filename):
        ext_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return jsonify({"error": f"Format tidak didukung. Gunakan: {ext_list}"}), 400

    model_size = request.form.get("model", "large-v3")
    language   = request.form.get("language", "") or None
    prompt     = request.form.get("prompt", "").strip() or None
    beam_size  = int(request.form.get("beam_size", 5))

    suffix = "." + f.filename.rsplit(".", 1)[1].lower()
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.save(tmp.name)
    tmp.close()

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "progress": 0,
        "status": "running",
        "message": "Mengupload selesai, menyiapkan...",
        "result": None,
        "language": "",
    }

    t = threading.Thread(
        target=run_transcribe,
        args=(job_id, tmp.name, model_size, language, prompt, beam_size),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    def generate():
        while True:
            job = jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Job tidak ditemukan'})}\n\n"
                return
            yield f"data: {json.dumps(job)}\n\n"
            if job["status"] in ("done", "error"):
                jobs.pop(job_id, None)
                return
            time.sleep(0.4)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
