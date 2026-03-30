# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
D:/Projects/Python/lively/
├── api.py                 # Main FastAPI application entry point
├── generate_audio.py      # Audio generation with VoxCPM
├── parse_text.py          # Novel text parsing and AI analysis
├── scheduler_tasks.py     # APScheduler task management
├── logger.py              # Dual-output logging (console + file)
├── requirements.txt       # Python dependencies
├── bean/                  # Database models (Peewee ORM)
├── utils/                 # Utilities (config, common functions)
├── config/                # JSON configuration files
├── admin/                 # Vue.js frontend application
├── audios/                # Generated audio files directory
├── logs/                  # Runtime log files
├── save/                  # Saved data (backup)
├── backup/                # Backup files (JSON)
├── temp/                  # Temporary files
└── asset/                 # Static assets (prompts)
```

## Directory Purposes

**Root Python Files:**
- Purpose: Core application logic
- Contains: `api.py`, `generate_audio.py`, `parse_text.py`, `scheduler_tasks.py`, `logger.py`

**`bean/`:**
- Purpose: Database models and ORM
- Contains: `beans.py` with Peewee models
- Key models: `Novel`, `Role`, `NovelName`, `RoleAudio`, `ScheduledTask`

**`utils/`:**
- Purpose: Shared utility functions
- Contains: `config.py` (JSON config loader), `common.py` (text processing helpers)

**`config/`:**
- Purpose: Application configuration storage
- Contains: `lively_config.json` (database, API keys, model settings)
- Note: Never commit secrets to this file

**`admin/`:**
- Purpose: Vue.js admin frontend
- Contains: `src/` (Vue source), `dist/` (built output), `node_modules/`

**`audios/`:**
- Purpose: Character audio samples storage
- Contains: Subdirectories per character (e.g., `奈奈见/audio.wav`, `三月七/audio.wav`)

**`logs/`:**
- Purpose: Runtime log files
- Contains: Timestamp-named log files (auto-generated)
- Note: Can be deleted, recreated on restart

**`save/`:**
- Purpose: Data persistence directory
- Contains: Saved state data

**`backup/`:**
- Purpose: Backup JSON files
- Contains: `temp*.json` files

**`temp/`:**
- Purpose: Temporary file storage
- Contains: Runtime temporary data

**`asset/`:**
- Purpose: Static prompt templates
- Contains: `prompt.txt` for AI analysis prompts

## Key File Locations

**Entry Points:**
- `D:/Projects/Python/lively/api.py`: Main API server (port 6888)
- `D:/Projects/Python/lively/admin/src/main.js`: Vue app bootstrap

**Configuration:**
- `D:/Projects/Python/lively/config/lively_config.json`: Application settings

**Database Models:**
- `D:/Projects/Python/lively/bean/beans.py`: All Peewee model definitions

**Core Logic:**
- `D:/Projects/Python/lively/parse_text.py`: Text parsing and AI integration
- `D:/Projects/Python/lively/generate_audio.py`: Audio generation pipeline
- `D:/Projects/Python/lively/scheduler_tasks.py`: Background task scheduler

**Frontend:**
- `D:/Projects/Python/lively/admin/src/App.vue`: Root Vue component with layout
- `D:/Projects/Python/lively/admin/src/router/index.js`: Vue Router config
- `D:/Projects/Python/lively/admin/src/api/index.js`: Axios API client
- `D:/Projects/Python/lively/admin/src/views/`: Vue page components

**Testing:** Not detected (no test framework configured)

## Naming Conventions

**Python Files:**
- snake_case: `parse_text.py`, `generate_audio.py`, `scheduler_tasks.py`
- singular noun: `api.py`, `logger.py`

**Python Modules:**
- snake_case: `bean/beans.py`, `utils/config.py`

**Vue Files:**
- PascalCase: `App.vue`, `NovelManage.vue`, `RoleAudioManage.vue`

**Directories:**
- lowercase: `bean/`, `utils/`, `admin/src/views/`

**Database Tables (Peewee):**
- snake_case singular: `novels`, `roles`, `novel_names`, `role_audios`, `scheduled_tasks`

## Where to Add New Code

**New API Endpoint:**
- Location: `D:/Projects/Python/lively/api.py`
- Add new `@app.*` decorated function
- Follow existing patterns for Pydantic models and error handling

**New Database Model:**
- Location: `D:/Projects/Python/lively/bean/beans.py`
- Add new class extending `BaseModel`
- Call `db.create_tables()` if new model

**New Frontend View:**
- Location: `D:/Projects/Python/lively/admin/src/views/`
- Create new `.vue` file with PascalCase name
- Add route in `admin/src/router/index.js`
- Add API methods in `admin/src/api/index.js`

**New Utility Function:**
- Location: `D:/Projects/Python/lively/utils/common.py` (for text/processing helpers)
- Location: `D:/Projects/Python/lively/utils/config.py` (for config helpers)

**New Scheduled Task:**
- Location: `D:/Projects/Python/lively/scheduler_tasks.py`
- Add job functions and management functions
- Expose via API endpoints in `api.py`

## Frontend vs Backend Separation

**Backend (Python):**
- Framework: FastAPI with Pydantic
- ORM: Peewee with SQLite
- Task Queue: APScheduler (AsyncIOScheduler)
- AI Integration: Anthropic client + VoxCPM local model
- Audio Processing: pydub, soundfile, numpy
- Entry: `api.py` runs on port 6888

**Frontend (Vue.js):**
- Framework: Vue 3 with Composition API
- UI Library: Element Plus
- Router: Vue Router 4
- HTTP Client: Axios
- Build: Vite (implied by admin structure)
- Entry: `admin/src/main.js`
- Built output: `admin/dist/`

**Integration:**
- Frontend calls `/api/*` endpoints via axios
- Frontend receives WebSocket events at `/ws/logs`
- Backend serves built frontend at `/` and static assets at `/assets/`
- Backend also serves audio files at `/audios/`

## Module Organization

**Data Flow Modules:**
```
parse_text.py (text parsing)
    ↓
bean/beans.py (data models)
    ↓
generate_audio.py (audio generation)
    ↓
api.py (API + serving)
```

**Admin Frontend Modules:**
```
main.js (bootstrap)
    ↓
App.vue (layout)
    ↓
router/index.js (routing)
    ↓
views/*.vue (pages)
    ↓
api/index.js (HTTP calls)
```

---

*Structure analysis: 2026-03-30*
