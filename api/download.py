import json
import os
import re
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path


def build_format_string(resolution: str, fps: str) -> str:
    height_map = {
        "360p": 360,
        "480p": 480,
        "720p": 720,
        "1080p": 1080,
        "1440p": 1440,
        "4K": 2160,
    }
    height = height_map.get(resolution, 720)
    max_fps = 60 if fps == "60fps" else 30
    return f"bestvideo[height<={height}][fps<={max_fps}]+bestaudio/best[height<={height}][fps<={max_fps}]/best[height<={height}]"


def sanitize_filename(name: str) -> str:
    # Remove unsafe path chars and control chars for Content-Disposition.
    clean = re.sub(r"[\\/:*?\"<>|\r\n]+", "_", name).strip(" .")
    return clean or "video"


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/download":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        url = (payload.get("url") or "").strip()
        resolution = (payload.get("resolution") or "720p").strip()
        fps = (payload.get("fps") or "30fps").strip()

        if not url:
            self._send_json({"error": "URL is required"}, 400)
            return

        fmt = build_format_string(resolution, fps)

        # Vercel allows writing only to /tmp.
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

            # Optional runtime tuning through env vars on Vercel dashboard.
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
                self._send_json(
                    {
                        "error": "Download failed",
                        "details": tail,
                    },
                    500,
                )
                return

            files = list(Path(tmp_dir).glob("out.*"))
            if not files:
                self._send_json({"error": "No output file found"}, 500)
                return

            out_file = files[0]
            file_bytes = out_file.read_bytes()

            video_name = sanitize_filename(payload.get("filename") or "youtube_video")
            if out_file.suffix.lower() == ".mp4":
                download_name = f"{video_name}.mp4"
                content_type = "video/mp4"
            else:
                download_name = f"{video_name}{out_file.suffix}"
                content_type = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(file_bytes)))
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.end_headers()
            self.wfile.write(file_bytes)

    def do_GET(self):
        self.send_error(405)

    def log_message(self, format, *args):
        return

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
