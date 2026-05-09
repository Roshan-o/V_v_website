# Video-to-Video Dubbing & Translation Pipeline

An end-to-end web application for automated video translation and dubbing. This tool allows users to upload a video, transcribe its audio, translate the text into a target language (primarily Indian languages), and generate a new dubbed video with high-quality synthesized speech.

## Features

- **Automated Pipeline**: Seamlessly handles extraction, transcription, translation, and dubbing.
- **High-Quality ASR**: Uses OpenAI's Whisper for robust speech-to-text transcription.
- **Multilingual Support**: Supports translation between English and 22 official Indian languages using AI4Bharat's IndicTrans2.
- **Natural Dubbing**: Generates natural-sounding voices using Svara-TTS and Edge-TTS.
- **Real-time Tracking**: Monitor the progress of each stage (Extraction, Transcription, Translation, Dubbing) via the web interface.
- **Memory Efficient**: Optimized with GPU memory management (CUDA cache clearing) for large video files.

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Video Processing**: MoviePy
- **AI Models**:
  - **Transcription**: `openai-whisper`
  - **Translation**: `indictrans2` (via AI4Bharat)
  - **TTS**: `Svara-TTS` & `edge-tts`
- **Execution**: Asynchronous background tasks with `uvicorn`

### Frontend
- **Framework**: React.js with TypeScript
- **Styling**: Vanilla CSS (Premium Design)
- **API Communication**: Axios

## Prerequisites

- Python 3.10+
- Node.js & npm
- FFmpeg (required for video/audio processing)
- NVIDIA GPU with CUDA support (Recommended for faster processing)

## Installation & Setup

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements_stable.txt
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend
```bash
cd backend
python main.py
```
The server will start at `http://localhost:8000`.

### Start the Frontend
```bash
cd frontend
npm start
```
The application will be available at `http://localhost:3000`.

## Project Structure

```text
.
├── backend/            # FastAPI server and AI processing scripts
│   ├── main.py         # Primary API entry point
│   ├── a_t.py          # Audio to Text (Whisper)
│   ├── t_t.py          # Text to Text (Translation)
│   ├── t_av.py         # Text to Audio/Video (TTS & Merge)
│   └── v_a.py          # Video to Audio extraction
├── frontend/           # React application
│   ├── src/            # Component and logic files
│   └── public/         # Static assets
└── language_support_report.md # Detailed language compatibility info
```
