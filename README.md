# YT Downloader (Vercel Ready)

Serverless YouTube downloader for Vercel using Python + yt-dlp, with a static frontend.

## Current Project Structure

```text
YTDOWNLOADER/
├── api/
│   └── download.py
├── static/
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── .vercelignore
├── requirements.txt
├── vercel.json
└── README.md
```

## How It Works

1. Frontend sends `POST /api/download` with `url`, `resolution`, and `fps`.
2. Serverless function runs yt-dlp in a temporary directory.
3. Response returns the video file directly as an attachment.

## Deploy to Vercel

1. Push this repository to GitHub.
2. Import the repository into Vercel.
3. Deploy with default settings.

## Optional Environment Variables

- `YTDLP_JS_RUNTIMES`
- `YTDLP_REMOTE_COMPONENTS`
- `YTDLP_EXTRACTOR_ARGS`
- `YTDLP_USER_AGENT`

Suggested values when needed:

- `YTDLP_JS_RUNTIMES=node`
- `YTDLP_REMOTE_COMPONENTS=ejs:github`
- `YTDLP_EXTRACTOR_ARGS=youtube:player_client=android,web`

## Notes

- This setup is optimized for Vercel serverless usage.
- Large/long videos can hit execution limits.
- No cookie files are required in this repo.
- Some videos may fail from datacenter IPs with a YouTube bot-check challenge.
