import os
import uuid
import json
import shutil
import asyncio
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing backend scripts
from v_a import videotoaudio
from a_t import AudioTOText
from t_t import textConversion
from t_av_without_emotion import AudioTOVideo

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

async def run_pipeline(job_id: str, video_path: str):
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Files paths
    audio_path = os.path.join(job_dir, "extracted_audio.wav")
    src_text_path = os.path.join(job_dir, "source_text.json")
    dst_text_path = os.path.join(job_dir, "translated_text.json")
    final_audio_path = os.path.join(job_dir, "final_telugu_audio.wav")
    output_video_path = os.path.join(job_dir, "output_video.mp4")
    
    try:
        # Stage 1: Extraction
        update_job(job_id, "extraction", "processing")
        videotoaudio(video_path, audio_path).convert()
        update_job(job_id, "extraction", "completed", "extracted_audio.wav")
        
        # Stage 2: Transcription
        update_job(job_id, "transcription", "processing")
        AudioTOText(audio_path, src_text_path).convert()
        update_job(job_id, "transcription", "completed", "source_text.json")
        
        # Stage 3: Translation
        update_job(job_id, "translation", "processing")
        # Using mock/default API key for sarvam if needed, or fallback to NLLB
        # For now, let's try the sarvam one if provided in code, else maybe we should have a way to pass it.
        # The user's code had "sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4"
        sarvam_api_key = "sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4" 
        textConversion(src_text_path, dst_text_path).convert_indictrans2("ai4bharat/indictrans2-en-indic-1B")
        update_job(job_id, "translation", "completed", "translated_text.json")
        
        # Stage 4: Dubbing (TTS + Merge)
        update_job(job_id, "dubbing", "processing")
        # AudioTOVideo(json_file, final_audio_file, video_file, output_video)
        AudioTOVideo(dst_text_path, final_audio_path, video_path, output_video_path).convert()
        update_job(job_id, "dubbing", "completed", "output_video.mp4")
        
        jobs[job_id]["status"] = "completed"
        
    except Exception as e:
        print(f"Error in pipeline for job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error_message"] = str(e)

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    video_path = os.path.join(job_dir, "input_video.mp4")
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
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
    
    background_tasks.add_task(run_pipeline, job_id, video_path)
    
    return {"job_id": job_id}

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
