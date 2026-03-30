# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Monolithic Python backend with Vue.js SPA frontend

**Key Characteristics:**
- FastAPI REST API backend serving both data and static frontend files
- SQLite database with Peewee ORM for persistence
- AI-powered text analysis pipeline using Claude API (MiniMax)
- VoxCPM local model for audio generation
- APScheduler for async task scheduling
- Vue 3 SPA frontend with Element Plus UI
- WebSocket support for real-time log streaming

## Layers

**API Layer (`api.py`):**
- Purpose: REST API endpoints and application lifecycle
- Location: `D:/Projects/Python/lively/api.py`
- Contains: FastAPI app, Pydantic models, all route handlers
- Depends on: bean, utils, scheduler_tasks, generate_audio, parse_text
- Used by: Vue.js frontend via axios

**Data Layer (`bean/beans.py`):**
- Purpose: Database models and ORM definitions
- Location: `D:/Projects/Python/lively/bean/beans.py`
- Contains: Novel, Role, NovelName, RoleAudio, ScheduledTask models
- Depends on: peewee, config
- Used by: api.py, parse_text.py, generate_audio.py, scheduler_tasks.py

**Text Processing Layer (`parse_text.py`):**
- Purpose: Novel text parsing and AI analysis
- Location: `D:/Projects/Python/lively/parse_text.py`
- Contains: Chapter segmentation, AI prompt construction, dialogue extraction
- Depends on: bean, utils.config, anthropic client
- Used by: api.py, scheduler_tasks.py

**Audio Generation Layer (`generate_audio.py`):**
- Purpose: Audio generation and silence removal
- Location: `D:/Projects/Python/lively/generate_audio.py`
- Contains: VoxCPM integration, audio segment processing, role audio loading
- Depends on: bean, utils.config, VoxCPM
- Used by: api.py, scheduler_tasks.py

**Task Scheduling Layer (`scheduler_tasks.py`):**
- Purpose: Background task management with APScheduler
- Location: `D:/Projects/Python/lively/scheduler_tasks.py`
- Contains: Job management, task status tracking, cron scheduling
- Depends on: apscheduler, bean
- Used by: api.py

**Configuration Layer (`utils/config.py`):**
- Purpose: Configuration loading from JSON
- Location: `D:/Projects/Python/lively/utils/config.py`
- Contains: JSON config reader with dot-notation access
- Used by: All modules

**Logging Layer (`logger.py`):**
- Purpose: Dual-output logging (console + file)
- Location: `D:/Projects/Python/lively/logger.py`
- Contains: Timestamp-based log files in `logs/` directory
- Used by: All modules

**Frontend Layer (`admin/`):**
- Purpose: Vue.js admin interface
- Location: `D:/Projects/Python/lively/admin/`
- Contains: Vue 3 SPA with Vue Router, Element Plus
- Entry: `admin/src/main.js`

## Data Flow

**Novel Upload and Processing Pipeline:**

1. **Upload** - User uploads TXT file via frontend
2. **Split** - `parse_text.py::split_novel_text_by_content_list()` splits by chapter markers
3. **Store** - Novel records created with `current_state=1` (segmented, pending analysis)
4. **Analyze** - AI (`parse_text.py::model_parse()`) extracts character dialogues
5. **Update** - Novel records updated to `current_state=2` (analyzed, pending synthesis)
6. **Bind** - User binds character roles to audio samples
7. **Generate** - `generate_audio.py::generate_chapter_audio()` creates audio segments
8. **Complete** - Novel records updated to `current_state=3` (synthesized)

**Request Flow:**

```
Frontend (Vue.js)
    ↓ HTTP/WebSocket
FastAPI (api.py)
    ↓ Pydantic validation
Peewee ORM (bean/beans.py)
    ↓
SQLite Database
```

**Task Execution Flow:**

```
API Request → scheduler_tasks.py → APScheduler
    ↓ (async)
parse_text.py / generate_audio.py
    ↓ (WebSocket)
Frontend Log Viewer
```

## Key Abstractions

**Novel State Machine:**
- State 1: `已分片待解析` (Segmented, pending AI analysis)
- State 2: `已解析待合成` (Analyzed, pending audio synthesis)
- State 3: `已合成语音` (Synthesized, audio complete)

**Role Audio Binding:**
- `Role.is_bind` indicates if character has associated audio
- `Role.bind_audio_name` references `RoleAudio.role_name`
- `RoleAudio.citation_count` tracks usage frequency

**Scheduled Tasks:**
- Types: `parse`, `generate`, `multithread-generate`, `watchdog`
- Managed via `ScheduledTask` model and APScheduler
- Support cron expressions for scheduling

## Entry Points

**Main API Server:**
- Location: `D:/Projects/Python/lively/api.py`
- Triggers: `uvicorn api:app` or `python api.py`
- Port: 6888
- Responsibilities: API routes, CORS, static file serving, lifespan management

**Database Initialization:**
- Location: `D:/Projects/Python/lively/bean/beans.py`
- Trigger: Module import at startup
- Creates tables if not exist: `novels`, `roles`, `novel_names`, `role_audios`, `scheduled_tasks`

**Frontend Build:**
- Location: `D:/Projects/Python/lively/admin/`
- Build output: `D:/Projects/Python/lively/admin/dist/`
- Served by FastAPI at `/` and `/assets/`

## Error Handling

**Strategy:** Exception propagation with HTTPException wrapping

**Patterns:**
- `try/except` blocks with `traceback.print_exc()` and `log_error()`
- `HTTPException` with status codes for API errors
- Database rollback on failure via `db.rollback()`
- Global exception handlers at API endpoints

## Cross-Cutting Concerns

**Logging:** Dual-output to console and file via `logger.py`
- Files stored in `logs/` with timestamp naming
- Separate `log()`, `log_error()`, `log_success()`, `log_warning()` functions

**Validation:** Pydantic models for request/response validation
- `NovelBase`, `RoleBase`, `NovelNameBase`, `RoleAudioBase` for creation
- `*Update` models with Optional fields for partial updates
- `ConfigDict(from_attributes=True)` for ORM-to-Pydantic conversion

**Authentication:** None detected (CORS allows all origins)

**Configuration:** JSON file at `config/lively_config.json`
- Database name, API keys, model parameters, token limits

---

*Architecture analysis: 2026-03-30*
