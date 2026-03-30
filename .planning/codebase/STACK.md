# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.12 - Backend API, audio processing, text parsing, scheduled tasks
- JavaScript/TypeScript - Frontend admin panel

**Secondary:**
- Vue 3 (Composition API) - Frontend UI framework

## Runtime

**Environment:**
- Python 3.12 with CUDA 12.8 (GPU acceleration for audio generation)
- Node.js (for frontend build)

**Package Manager:**
- pip (Python dependencies)
- npm (Node.js dependencies)
- Lockfile: `requirements.txt`

## Frameworks

**Core Backend:**
- FastAPI 0.135.1 - REST API framework
- Starlette 0.52.1 - ASGI framework (FastAPI dependency)
- Uvicorn 0.42.0 - ASGI server

**Frontend:**
- Vue 3.4.0 - Progressive JavaScript framework
- Vue Router 4.2.5 - SPA routing
- Element Plus 2.5.0 - UI component library
- Axios 1.6.0 - HTTP client

**Database:**
- Peewee 4.0.2 - Lightweight ORM
- SQLite - Database engine (via Peewee)

**AI/ML:**
- torch 2.10.0+cu128 - PyTorch with CUDA
- torchaudio 2.10.0+cu128 - Audio processing
- nano-vllm-voxcpm 1.0.1 - VoxCPM model serving
- transformers 5.3.0 - Hugging Face transformers

**Task Scheduling:**
- APScheduler 3.11.2 - AsyncIOScheduler for background jobs

**Audio Processing:**
- pydub 0.25.1 - Audio manipulation
- soundfile 0.13.1 - Audio file I/O

**Testing:**
- Not detected

**Build/Dev:**
- Vite 5.0.0 - Frontend build tool
- @vitejs/plugin-vue 5.0.0 - Vue support for Vite

## Key Dependencies

**Critical:**
- fastapi 0.135.1 - API framework
- pydantic 2.12.5 - Data validation
- peewee 4.0.2 - Database ORM
- anthropic 0.86.0 - Claude API client
- pydub 0.25.1 - Audio processing
- torch 2.10.0+cu128 - Deep learning framework

**Infrastructure:**
- uvicorn 0.42.0 - ASGI server
- APScheduler 3.11.2 - Job scheduling
- python-multipart 0.0.22 - File upload support
- python-dateutil 2.9.0 - Date utilities

## Configuration

**Environment:**
- JSON config file: `config/lively_config.json`
- Configuration fields:
  - `database_name`: SQLite database name
  - `api_key`: Anthropic/MiniMax API key
  - `base_url`: API endpoint URL
  - `model_name`: AI model name
  - `max_token`: Maximum token limit
  - `max_section_length`: Text chunk size
  - `preload_role_count`: Role preloading count

**Build:**
- `admin/vite.config.js` - Vite configuration for frontend
- Base path: `./` (for SPA deployment)
- Output: `admin/dist/`

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 18+
- CUDA-compatible GPU (for VoxCPM audio generation)
- Windows or Linux

**Production:**
- FastAPI application served via Uvicorn
- Static files served from `admin/dist/`
- SQLite database (file-based)
- GPU required for audio generation

---

*Stack analysis: 2026-03-30*
