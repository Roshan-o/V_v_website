import os
import uuid
import json
import shutil
import asyncio
import gc
import torch
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing backend scripts
from v_a import videotoaudio
from a_t import AudioTOText
from t_t import textConversion
from t_av import AudioTOVideo

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Status tracking
jobs: Dict[str, dict] = {}

class JobStatus(BaseModel):
    id: str
    status: str
    stages: Dict[str, str]  # stage_name -> status (pending, processing, completed, error)
    files: Dict[str, str]   # stage_name -> file_path

def update_job(job_id: str, stage: str, status: str, filename: str = None):
    jobs[job_id]["stages"][stage] = status
    if filename:
        jobs[job_id]["files"][stage] = f"/outputs/{job_id}/{filename}"
    if all(s == "completed" for s in jobs[job_id]["stages"].values()):
        jobs[job_id]["status"] = "completed"

async def run_initial_pipeline(job_id: str, video_path: str):
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Files paths
    audio_path = os.path.join(job_dir, "extracted_audio.wav")
    
    try:
        # Stage 1: Extraction
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "extraction", "processing")
        videotoaudio(video_path, audio_path).convert()
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "extraction", "completed", "extracted_audio.wav")
        
        jobs[job_id]["status"] = "waiting_for_conversion"
        
    except Exception as e:
        print(f"Error in initial pipeline for job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error_message"] = str(e)

async def run_conversion_pipeline(job_id: str):
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    video_path = os.path.join(job_dir, "input_video.mp4")
    audio_path = os.path.join(job_dir, "extracted_audio.wav")
    src_text_path = os.path.join(job_dir, "source_text.json")
    dst_text_path = os.path.join(job_dir, "translated_text.json")
    final_audio_path = os.path.join(job_dir, "final_telugu_audio.wav")
    output_video_path = os.path.join(job_dir, "output_video.mp4")
    src_audio_file = os.path.join(job_dir, "extracted_audio.wav")
    
    job_data = jobs[job_id]
    src_language = job_data["src_language"]
    target_language = job_data["target_language"]
    gender = job_data["gender"]

    try:
        jobs[job_id]["status"] = "processing"
        
        # Stage 2: Transcription
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "transcription", "processing")
        AudioTOText(audio_path, src_text_path, language=src_language).convert()
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "transcription", "completed", "source_text.json")
        
        # Clear memory after transcription
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        # Stage 3: Translation
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "translation", "processing")
        textConversion(src_text_path, dst_text_path, src_language=src_language, target_language=target_language).convert()
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "translation", "completed", "translated_text.json")
        
        # Clear memory after translation
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Stage 4: Dubbing (TTS + Merge)
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "dubbing", "processing")
        AudioTOVideo(dst_text_path, final_audio_path, video_path, output_video_path, src_audio_file).convert_with_svara_tts(
            default_language=target_language, 
            default_gender=gender
        )
        if jobs[job_id]["status"] == "cancelled": return
        update_job(job_id, "dubbing", "completed", "output_video.mp4")
        
        jobs[job_id]["status"] = "completed"
        
    except Exception as e:
        print(f"Error in conversion pipeline for job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error_message"] = str(e)

@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    src_language: str = Form("English"),
    target_language: str = Form("Telugu"),
    gender: str = Form("Female")
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    video_path = os.path.join(job_dir, "input_video.mp4")
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
        "src_language": src_language,
        "target_language": target_language,
        "gender": gender,
        "stages": {
            "extraction": "pending",
            "transcription": "pending",
            "translation": "pending",
            "dubbing": "pending"
        },
        "files": {
            "original": f"/outputs/{job_id}/input_video.mp4"
        }
    }
    
    background_tasks.add_task(run_initial_pipeline, job_id, video_path)
    
    return {"job_id": job_id}

@app.post("/convert/{job_id}")
async def start_conversion(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]["stages"]["extraction"] != "completed":
        raise HTTPException(status_code=400, detail="Audio extraction not completed yet")
        
    background_tasks.add_task(run_conversion_pipeline, job_id)
    return {"status": "started"}

@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs[job_id]["status"] = "cancelled"
    return {"status": "cancelled"}

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

# Serve output files
app.mount("/outputs", StaticFiles(directory=UPLOAD_DIR), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
