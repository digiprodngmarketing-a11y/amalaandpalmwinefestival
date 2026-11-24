# Waves Stem Lab — separate audio service

This is an independent audio-processing application, separate from the Amala & Palmwine Festival marketing website.

## Features
- Accepts 1–30 audio uploads per batch (WAV, MP3, FLAC, M4A, AIFF, OGG).
- Uses Demucs htdemucs to produce vocals, drums, bass and other-instrument stems.
- Preserves original timing and duration. An optional target BPM is saved as a production reference; this version does not time-stretch or retime audio.
- Attempts BPM and dominant pitch-class analysis with librosa.
- Packages stems and a track-report.json in a ZIP for each track.

## Run locally
Requires Python 3.11+, FFmpeg, enough RAM and disk space. A GPU is recommended for large batches.

    cd stem-lab
    python -m venv .venv
    # Windows: .venv\\Scripts\\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. The first Demucs run downloads model weights.

## Docker
    docker build -t waves-stem-lab .
    docker run --rm -p 8000:8000 -v stem-data:/data waves-stem-lab

## API
- GET /api/health
- POST /api/separate — multipart files (repeat field, maximum 30) and optional target_bpm
- GET /api/jobs/{job_id}
- GET /api/jobs/{job_id}/download

## Hosting and safety
GitHub Pages only hosts static files; it cannot run Python, Demucs, PyTorch or process uploaded audio. Deploy this service separately to a Python-capable host with persistent disk and sufficient CPU/GPU. Before public use, add user authentication, rate limits, persistent job storage, a proper background queue, file-retention rules, backups and monitoring. This repository contains the application code; it is not yet a hosted audio-processing server.
