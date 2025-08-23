# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a video processing API service that converts videos into structured documents with transcriptions, summaries, and multimodal notes. The system processes uploaded videos through multiple stages including audio extraction, speech-to-text (ASR), text merging, summarization, and optional image-text note generation.

## Core Commands

### Start the API Service
```bash
python main.py
```
- Service runs on `http://localhost:8000`
- API documentation available at `http://localhost:8000/docs`
- Health check endpoint: `http://localhost:8000/api/health`

### Install Dependencies
```bash
pip install -r requirements.txt
```
**Note**: System requires `ffmpeg` binary installed (`brew install ffmpeg` on macOS)

### Run Tests
```bash
# Run the API test suite (requires service to be running)
python test_api.py

# Test with a specific video file
python test_api.py  # Uses upload/demo3.mp4 by default
```

### Frontend Development (React App)
```bash
# Navigate to frontend directory
cd zed-landing-vibe

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

## Project Architecture

### Service Layer Structure
The application follows a layered architecture with clear separation of concerns:

1. **API Layer** (`main.py`, `routers/`)
   - FastAPI application with CORS support
   - RESTful endpoints for upload, processing, status checking, and export
   - Background task processing for long-running operations

2. **Processing Pipeline** (`services/`)
   - `video_processor.py`: Orchestrates the entire workflow
   - `asr_tencent/`: Tencent Cloud ASR integration for speech-to-text
   - `text_merge.py`: Merges short ASR segments into coherent paragraphs
   - `summary_generator.py`: Generates summaries using LLM (OpenRouter)
   - `multimodal_service.py`: Creates image-text notes with keyframe extraction
   - `video_downloader.py`: Handles online video downloads (YouTube, Bilibili)

3. **Task Management**
   - `task_manager.py`: Manages task lifecycle and metadata
   - `task_logger.py`: Per-task logging with file and console output
   - Tasks stored in `storage/tasks/{task_id}/` directories

### Processing Workflow
The video processing pipeline executes these steps sequentially:

1. **Audio Extraction**: Uses ffmpeg to extract audio from video
2. **ASR Transcription**: Converts speech to text using Tencent Cloud ASR
3. **Text Merging**: Combines short utterances into meaningful paragraphs
4. **Summary Generation**: Creates section-wise summaries using LLM
5. **Multimodal Notes** (optional): Extracts keyframes and generates visual notes

### Environment Configuration
Required environment variables (in `.env`):
- `TENCENT_APPID`, `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`: For ASR service
- `COHERE_API_KEY`: For image processing in multimodal notes
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`: For LLM (using OpenRouter)
- `MODEL_ID`: LLM model identifier (e.g., `mistralai/ministral-8b`)

### API Endpoints

#### Core Processing Flow
1. `POST /api/upload` - Upload video file
2. `POST /api/process/{task_id}` - Start processing
3. `GET /api/status/{task_id}` - Check processing status
4. `GET /api/results/{task_id}` - Get JSON results
5. `GET /api/export/{task_id}/markdown` - Export as Markdown

#### Online Video Support
- `POST /api/download-url` - Download and process from URL
- `GET /api/download-status/{task_id}` - Check download progress
- `POST /api/preview-video` - Preview video metadata

#### Streaming
- `GET /api/stream-summary/{task_id}` - Stream full summary generation

### Output Structure
Each processed video creates these files in `storage/tasks/{task_id}/`:
- `original_video.mp4` - Original uploaded video
- `asr_result.json` - Raw transcription with timestamps
- `merged_text.json` - Paragraph-merged text
- `summary.json` - Section summaries
- `multimodal_notes.json` - Image-text note data
- `notes.md` - Final Markdown document
- `frames/` - Extracted keyframe images

## Development Tips

### Adding New Processing Steps
1. Create service class in `services/` directory
2. Add initialization in `VideoProcessingWorkflow._init_services()`
3. Insert processing step in `VideoProcessingWorkflow.process_video()`
4. Update task status tracking in processing pipeline

### Testing Video Processing
- Use `test_api.py` for end-to-end API testing
- Place test videos in `upload/` directory
- Monitor logs in `video_processing.log` and task-specific logs

### Working with Task Logs
Each task has its own log file in `storage/tasks/{task_id}/task.log` for debugging specific processing issues.

### Frontend Integration
The React app in `zed-landing-vibe/` uses:
- Vite as build tool
- Shadcn/ui components
- TailwindCSS for styling
- React Query for API state management

## Key File Patterns
- API routes: `routers/*.py`
- Processing services: `services/*.py`
- Data models: `models/*.py`
- Utility functions: `utils/*.py`
- Frontend source: `zed-landing-vibe/src/`
- Test files: `test_api.py`

## Common Issues and Solutions

### FFmpeg Not Found
Ensure ffmpeg is installed: `ffmpeg -version`

### ASR Service Fails
Check Tencent Cloud credentials in `.env` file

### Multimodal Notes Not Generated
Verify `COHERE_API_KEY` is set and `enable_multimodal=true` in process request

### Large Video Processing Timeout
Videos over 500MB may take significant time; monitor via `/api/status/{task_id}`
