from __future__ import annotations
import json, os, subprocess, threading, uuid, zipfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parent
DATA=Path(os.getenv("STEM_DATA_DIR",ROOT/"data")).resolve()
INBOX,WORK,EXPORTS=DATA/"uploads",DATA/"work",DATA/"exports"
for p in (INBOX,WORK,EXPORTS): p.mkdir(parents=True,exist_ok=True)
MAX_BYTES=int(os.getenv("MAX_FILE_BYTES",str(500*1024*1024)))
ALLOWED={".wav",".mp3",".flac",".m4a",".aiff",".aif",".ogg"}
JOBS:dict[str,dict]={}; LOCK=threading.Lock()
app=FastAPI(title="Waves Stem Lab API",version="1.0.0")
app.mount("/",StaticFiles(directory=ROOT/"web",html=True),name="web")

def update(jid,**values):
    with LOCK: JOBS[jid].update(values)

def analyse(path:Path)->dict:
    result={"filename":path.name}
    try:
        import librosa
        y,sr=librosa.load(str(path),sr=None,mono=True,duration=180)
        tempo,_=librosa.beat.beat_track(y=y,sr=sr)
        chroma=librosa.feature.chroma_stft(y=y,sr=sr).mean(axis=1)
        notes=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        result.update({"sample_rate":sr,"duration_seconds":round(float(librosa.get_duration(y=y,sr=sr)),2),
          "estimated_bpm":round(float(tempo),1),"dominant_pitch_class":notes[int(chroma.argmax())]})
    except Exception as exc: result["analysis_note"]=str(exc)[:300]
    return result

def process(jid,source:Path,target_bpm:Optional[float]):
    folder=WORK/jid; folder.mkdir(parents=True,exist_ok=True)
    try:
        update(jid,status="analysing",progress=8,message="Reading audio and estimating tempo/key…")
        report_analysis=analyse(source)
        update(jid,status="separating",progress=24,analysis=report_analysis,message="Separating vocals, drums, bass and other instruments…")
        cmd=[os.getenv("PYTHON","python"),"-m","demucs","-n","htdemucs","--out",str(folder),str(source)]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=int(os.getenv("SEPARATION_TIMEOUT","7200")))
        if proc.returncode: raise RuntimeError((proc.stderr or proc.stdout or "Demucs separation failed")[-1800:])
        dirs=list(folder.glob("htdemucs/*"))
        if not dirs: raise RuntimeError("Demucs completed but no output folder was found.")
        stemdir=dirs[0]; stems=[p for p in stemdir.iterdir() if p.suffix.lower() in {".wav",".mp3",".flac"}]
        if not stems: raise RuntimeError("No stem audio files were produced.")
        report={"job_id":jid,"source_file":source.name,"target_bpm_reference":target_bpm,
          "timing_policy":"Original tempo and duration preserved. Target BPM is reference only; no time-stretching applied.",
          "analysis":report_analysis,"stems":[p.name for p in stems]}
        (stemdir/"track-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        archive=EXPORTS/f"{jid}-stems.zip"
        with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
            for p in stemdir.iterdir():
                if p.is_file(): z.write(p,p.name)
        update(jid,status="complete",progress=100,message="Stems and track report are ready.",
          download_url=f"/api/jobs/{jid}/download",stems=[p.name for p in stems],report=report)
    except subprocess.TimeoutExpired: update(jid,status="failed",progress=100,message="Separation timed out. Try a shorter or smaller file.")
    except Exception as exc: update(jid,status="failed",progress=100,message=str(exc)[:2000])
    finally: source.unlink(missing_ok=True)

@app.get("/api/health")
def health(): return {"ok":True,"service":"Waves Stem Lab","engine":"Demucs htdemucs"}

@app.post("/api/separate")
async def separate(background:BackgroundTasks,files:list[UploadFile]=File(...),target_bpm:Optional[float]=Form(None)):
    if not files or len(files)>30: raise HTTPException(400,"Upload between 1 and 30 audio files per batch.")
    if target_bpm is not None and not 30<=target_bpm<=300: raise HTTPException(400,"Target BPM must be between 30 and 300.")
    created=[]
    for upload in files:
        suffix=Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED: raise HTTPException(415,f"Unsupported format: {upload.filename}")
        jid=uuid.uuid4().hex; source=INBOX/f"{jid}{suffix}"; size=0
        with source.open("wb") as out:
            while chunk:=await upload.read(1024*1024):
                size+=len(chunk)
                if size>MAX_BYTES:
                    source.unlink(missing_ok=True); raise HTTPException(413,f"{upload.filename} exceeds upload limit.")
                out.write(chunk)
        if not size: source.unlink(missing_ok=True); raise HTTPException(400,f"{upload.filename} is empty.")
        with LOCK: JOBS[jid]={"job_id":jid,"filename":upload.filename,"status":"queued","progress":0,"message":"Waiting for worker…","target_bpm_reference":target_bpm}
        background.add_task(process,jid,source,target_bpm)
        created.append({"job_id":jid,"filename":upload.filename,"status":"queued"})
    return {"jobs":created,"message":"Batch accepted."}

@app.get("/api/jobs/{jid}")
def status(jid:str):
    with LOCK: job=JOBS.get(jid)
    if not job: raise HTTPException(404,"Job not found. In-memory jobs reset when the server restarts.")
    return job

@app.get("/api/jobs/{jid}/download")
def download(jid:str):
    path=EXPORTS/f"{jid}-stems.zip"
    if not path.is_file(): raise HTTPException(404,"Stems archive is not ready.")
    return FileResponse(path,media_type="application/zip",filename=f"{jid}-stems.zip")
