import os
import subprocess
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from api.download import build_format_string, sanitize_filename


app = Flask(__name__, static_folder="static", static_url_path="")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def run_yt_dlp(url: str, out_template: str, fmt: str, extractor_args: str) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--newline",
        "--no-colors",
        "--force-ipv4",
        "--socket-timeout",
        "20",
        "--sleep-requests",
        "1",
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
    ]

    if extractor_args:
        cmd.extend(["--extractor-args", extractor_args])

    user_agent = os.getenv("YTDLP_USER_AGENT", DEFAULT_USER_AGENT).strip()
    if user_agent:
        cmd.extend(["--user-agent", user_agent])

    js_runtimes = os.getenv("YTDLP_JS_RUNTIMES", "").strip()
    if js_runtimes:
        cmd.extend(["--js-runtimes", js_runtimes])

    remote_components = os.getenv("YTDLP_REMOTE_COMPONENTS", "").strip()
    if remote_components:
        cmd.extend(["--remote-components", remote_components])

    cmd.append(url)

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


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
    extractor_args = os.getenv("YTDLP_EXTRACTOR_ARGS", "youtube:player_client=android,web").strip()

    with tempfile.TemporaryDirectory(prefix="ytdl_") as tmp_dir:
        out_template = str(Path(tmp_dir) / "out.%(ext)s")

        logs = []
        attempts = [
            (fmt, extractor_args),
            ("18/best[height<=360]/best", extractor_args),
        ]

        proc = None
        for attempt_fmt, attempt_extractor_args in attempts:
            proc = run_yt_dlp(url, out_template, attempt_fmt, attempt_extractor_args)
            logs.append(proc.stdout or "")

            if proc.returncode == 0:
                break

            # Clear partially downloaded output before next retry strategy.
            for partial in Path(tmp_dir).glob("out.*"):
                try:
                    partial.unlink()
                except OSError:
                    pass

        if proc is None or proc.returncode != 0:
            full_log = "\n".join(logs)
            tail = "\n".join(full_log.splitlines()[-16:])

            if "Sign in to confirm you\u2019re not a bot" in full_log or "Sign in to confirm you're not a bot" in full_log:
                return (
                    jsonify(
                        {
                            "error": "YouTube blocked this request from the server IP (bot check)",
                            "details": tail,
                        }
                    ),
                    429,
                )

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
