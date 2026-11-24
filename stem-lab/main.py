from __future__ import annotations

import json
import os
import subprocess
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv("STEM_DATA_DIR", str(ROOT / "data"))).resolve()
UPLOADS, WORK, EXPORTS = DATA / "uploads", DATA / "work", DATA / "exports"
for directory in (UPLOADS, WORK, EXPORTS):
    directory.mkdir(parents=True, exist_ok=True)

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(500 * 1024 * 1024)))
MAX_BATCH_FILES = int(os.getenv("MAX_BATCH_FILES", "30"))
SEPARATION_TIMEOUT = int(os.getenv("SEPARATION_TIMEOUT", "7200"))
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif", ".ogg"}
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

app = FastAPI(title="Waves Stem Lab API", version="1.1.0")


def set_job(job_id: str, **updates) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def analyse_audio(path: Path) -> dict:
    """Best-effort BPM and key estimate; separation remains available if analysis fails."""
    result = {"filename": path.name}
    try:
        import librosa
        import soundfile as sf

        info = sf.info(str(path))
        audio, sample_rate = librosa.load(str(path), sr=None, mono=True, duration=180)
        tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
        chroma = librosa.feature.chroma_stft(y=audio, sr=sample_rate).mean(axis=1)
        pitch_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        tempo_value = float(tempo[0]) if getattr(tempo, "ndim", 0) else float(tempo)
        result.update({
            "duration_seconds": round(float(info.duration), 2),
            "sample_rate": int(sample_rate),
            "estimated_bpm": round(tempo_value, 1),
            "dominant_pitch_class": pitch_names[int(chroma.argmax())],
        })
    except Exception as exc:
        result["analysis_note"] = f"Analysis unavailable: {str(exc)[:240]}"
    return result


def process_job(job_id: str, source: Path, original_name: str, target_bpm: Optional[float]) -> None:
    job_dir = WORK / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        set_job(job_id, status="analysing", progress=5, message="Analysing audio…")
        analysis = analyse_audio(source)
        set_job(job_id, status="separating", progress=18, analysis=analysis,
                message="Demucs is separating vocals, drums, bass and other instruments…")

        command = [
            os.getenv("PYTHON", "python"), "-m", "demucs",
            "-n", "htdemucs", "--out", str(job_dir), str(source),
        ]
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=SEPARATION_TIMEOUT, check=False
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "Demucs separation failed")[-1600:]
            raise RuntimeError(detail)

        output_dirs = list((job_dir / "htdemucs").glob("*"))
        if not output_dirs:
            raise RuntimeError("Demucs finished but no stem output directory was found.")
        stem_files = sorted(
            p for p in output_dirs[0].iterdir()
            if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac"}
        )
        if not stem_files:
            raise RuntimeError("Demucs did not produce any stem audio files.")

        report = {
            "job_id": job_id,
            "source_file": original_name,
            "analysis": analysis,
            "target_bpm_reference": target_bpm,
            "tempo_policy": (
                "Stems preserve the source recording's timing and duration. "
                "Target BPM is recorded as a reference only; automatic time-stretching is not applied."
            ),
            "separation_model": "htdemucs",
            "stems": [p.name for p in stem_files],
        }
        (output_dirs[0] / "track-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

        archive = EXPORTS / f"{job_id}-stems.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for item in sorted(output_dirs[0].iterdir()):
                if item.is_file():
                    bundle.write(item, arcname=item.name)

        set_job(
            job_id, status="complete", progress=100,
            message="Your stems and track report are ready.",
            download_url=f"/api/jobs/{job_id}/download",
            stems=[p.name for p in stem_files], report=report,
        )
    except subprocess.TimeoutExpired:
        set_job(job_id, status="failed", progress=100,
                message="Separation timed out. Try a shorter file or a larger processing server.")
    except Exception as exc:
        set_job(job_id, status="failed", progress=100, message=str(exc)[:1800])
    finally:
        source.unlink(missing_ok=True)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "Waves Stem Lab", "engine": "Demucs htdemucs"}


@app.post("/api/separate")
async def separate(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    target_bpm: Optional[float] = Form(None),
):
    if not files or len(files) > MAX_BATCH_FILES:
        raise HTTPException(400, f"Upload between 1 and {MAX_BATCH_FILES} audio files per batch.")
    if target_bpm is not None and not 30 <= target_bpm <= 300:
        raise HTTPException(400, "Target BPM must be between 30 and 300.")

    accepted = []
    for upload in files:
        original_name = Path(upload.filename or "audio").name
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"Unsupported audio format for {original_name}.")

        job_id = uuid.uuid4().hex
        destination = UPLOADS / f"{job_id}{extension}"
        total = 0
        try:
            with destination.open("wb") as output:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise HTTPException(413, f"{original_name} exceeds the per-file upload limit.")
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if total == 0:
            destination.unlink(missing_ok=True)
            raise HTTPException(400, f"{original_name} is empty.")

        with JOBS_LOCK:
            JOBS[job_id] = {
                "job_id": job_id, "filename": original_name, "status": "queued",
                "progress": 0, "message": "Waiting for the processing worker…",
                "target_bpm_reference": target_bpm,
            }
        background.add_task(process_job, job_id, destination, original_name, target_bpm)
        accepted.append({"job_id": job_id, "filename": original_name, "status": "queued"})

    return {"jobs": accepted, "message": "Your batch has been accepted."}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found. Job status is currently held in server memory.")
        return dict(job)


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str):
    archive = EXPORTS / f"{job_id}-stems.zip"
    if not archive.is_file():
        raise HTTPException(404, "The stems ZIP is not ready yet.")
    return FileResponse(
        archive, media_type="application/zip", filename=f"{job_id}-stems.zip"
    )


# Mount the UI last so it never intercepts /api/* requests.
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
