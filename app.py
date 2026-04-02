import os
import subprocess
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from api.download import build_format_string, sanitize_filename


app = Flask(__name__, static_folder="static", static_url_path="")


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/styles.css")
def styles():
    return send_from_directory("static", "styles.css")


@app.get("/script.js")
def script():
    return send_from_directory("static", "script.js")


@app.post("/api/download")
def download():
    payload = request.get_json(silent=True) or {}

    url = (payload.get("url") or "").strip()
    resolution = (payload.get("resolution") or "720p").strip()
    fps = (payload.get("fps") or "30fps").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    fmt = build_format_string(resolution, fps)

    with tempfile.TemporaryDirectory(prefix="ytdl_") as tmp_dir:
        out_template = str(Path(tmp_dir) / "out.%(ext)s")

        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--newline",
            "--no-colors",
            "--retries",
            "15",
            "--fragment-retries",
            "15",
            "--merge-output-format",
            "mp4",
            "-f",
            fmt,
            "-o",
            out_template,
            url,
        ]

        js_runtimes = os.getenv("YTDLP_JS_RUNTIMES", "").strip()
        if js_runtimes:
            cmd.extend(["--js-runtimes", js_runtimes])

        remote_components = os.getenv("YTDLP_REMOTE_COMPONENTS", "").strip()
        if remote_components:
            cmd.extend(["--remote-components", remote_components])

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.returncode != 0:
            tail = "\n".join(proc.stdout.splitlines()[-10:])
            return jsonify({"error": "Download failed", "details": tail}), 500

        files = list(Path(tmp_dir).glob("out.*"))
        if not files:
            return jsonify({"error": "No output file found"}), 500

        out_file = files[0]
        video_name = sanitize_filename(payload.get("filename") or "youtube_video")
        download_name = f"{video_name}{out_file.suffix.lower()}"

        return send_file(
            out_file,
            as_attachment=True,
            download_name=download_name,
            mimetype="video/mp4" if out_file.suffix.lower() == ".mp4" else "application/octet-stream",
        )
