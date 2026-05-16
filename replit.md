# LooksMaxxing AI Bot

A Telegram bot that analyzes facial features using computer vision and generates a detailed PDF report with scores, measurements, and personalized looksmaxxing advice. Paid feature using Telegram Stars (50 Stars per report).

## Run & Operate

- `cd bot/src && python bot.py` — run the Telegram bot (via "LooksMaxxing Bot" workflow)
- Required env: `TELEGRAM_BOT_TOKEN` — Telegram bot token from @BotFather

## Stack

- Python 3.11
- python-telegram-bot 22.7 (with Telegram Stars payments)
- MediaPipe 0.10 (Tasks API — FaceLandmarker) for facial landmark detection
- OpenCV (opencv-python-headless) for image processing
- ReportLab for PDF generation
- NumPy / SciPy

## Where things live

- `bot/src/bot.py` — Main bot logic, handlers, payment flow
- `bot/src/face_analyzer.py` — Facial geometry analysis (golden ratio, symmetry, thirds, canthal tilt, jaw)
- `bot/src/pdf_generator.py` — PDF report generation with dark theme, score bars, advice
- `bot/src/payments.py` — Payment constants (50 Stars per report)
- `bot/src/storage.py` — Pending photo persistence (file-based JSON)
- `bot/assets/face_landmarker.task` — MediaPipe face landmarker model (3.6MB)
- `bot/data/` — Runtime storage (gitignored)

## Architecture decisions

- MediaPipe 0.10 Tasks API (not the old `solutions` API) — requires model file download
- Telegram Stars (XTR currency) for payments — no external payment processor needed
- Photo stored by Telegram file_id; analysis runs after payment confirmed
- Analysis runs in asyncio thread pool executor to avoid blocking the event loop
- Pre-check face detection before asking for payment (free gate)

## Product

Users send a front-facing photo to the bot. A free face detection check runs first. If a face is found, they pay 50 Telegram Stars. After payment, the bot runs full facial geometry analysis and returns:
1. An annotated photo with landmark overlays and score overlay
2. A dark-themed PDF report with scores, measurements table, bar charts, and personalized advice

## Gotchas

- Always run `python bot.py` from `bot/src/` so relative paths to `../assets/` resolve correctly
- MediaPipe Tasks API requires the `.task` model file — it's at `bot/assets/face_landmarker.task`
- Telegram Stars payments use currency `"XTR"` — do not use `provider_token` (leave empty)
- `python-telegram-bot[payments]` extra is required for `LabeledPrice` and invoice support
