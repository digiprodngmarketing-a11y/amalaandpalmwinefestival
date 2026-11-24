# Waves Stem Lab — independent audio-processing application

Waves Stem Lab is separate from the Amala & Palmwine Festival website.

## Current capabilities
- Upload 1–30 audio tracks in one batch (WAV, MP3, FLAC, M4A, AIFF, OGG).
- Separate each track with Demucs `htdemucs` into vocals, drums, bass and other instruments.
- Attempt BPM and dominant pitch-class analysis with librosa.
- Package each track's stems and a `track-report.json` into an individual ZIP.
- Record an optional target BPM as a production reference.

**Tempo handling:** this version preserves the original recording timing and duration. Entering 96 BPM (or another target) records the desired reference in the report; it does not yet time-stretch audio to that tempo. Do not treat the BPM/key estimates as authoritative without listening and checking them.

## Run locally
Requires Python 3.11+, FFmpeg, libsndfile, adequate RAM and disk. A GPU is recommended for faster processing.

```powershell
cd stem-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The first Demucs run downloads model weights.

## Docker
```bash
docker build -t waves-stem-lab .
docker run --rm -p 8000:8000 -v stem-data:/data waves-stem-lab
```

## API
- `GET /api/health`
- `POST /api/separate` — multipart field `files` (repeat for each file), optional `target_bpm`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download`

## Important deployment notes
GitHub Pages is static hosting and cannot execute Python, PyTorch or Demucs. The website and this backend must be hosted separately. The backend code is not yet a publicly hosted processing service.

This repository version is a functional starter, not a hardened multi-user production service. Job state is held in memory and can be lost on restart; processing runs in FastAPI background tasks. Before accepting public uploads, deploy behind authentication/rate limits with persistent job storage, a real task queue, storage quotas, automatic retention/cleanup, monitoring and adequate CPU/GPU capacity. Never upload audio you do not have rights to process.
