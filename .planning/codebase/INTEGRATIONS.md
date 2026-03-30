# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**AI Text Processing:**
- Anthropic API (via MiniMax endpoint) - Claude AI for novel text parsing and role analysis
  - SDK/Client: `anthropic` Python package
  - Auth: API key stored in `config/lively_config.json`
  - Endpoint: `https://api.minimaxi.com/anthropic`
  - Used in: `parse_text.py`, `utils/common.py`

**AI Audio Generation:**
- VoxCPM (local model) - Text-to-speech generation
  - Implementation: `nanovllm-voxcpm` package
  - Model path: `./VoxCPM1.5/` (downloaded separately)
  - GPU: Requires CUDA with 95% memory utilization
  - Used in: `api.py` (server startup), `scheduler_tasks.py` (watchdog reload)
  - Configured in: `api.py` lines 194-202

## Data Storage

**Database:**
- SQLite
  - Location: Project root (configurable via `config/lively_config.json`)
  - ORM: Peewee
  - Tables: `novels`, `roles`, `novel_names`, `role_audios`, `scheduled_tasks`
  - Client: `bean/beans.py` defines models and `get_db()` function
  - WAL mode enabled for concurrent access

**File Storage:**
- Local filesystem
  - Audio files: `audios/{character_name}/audio.wav`
  - Novel text files: User-uploaded
  - Logs: `logs/` directory

**Caching:**
- None detected (in-memory job stores only)

## Authentication & Identity

**Auth Provider:**
- None (internal system only)
  - No user authentication detected
  - Admin panel is open access

## Monitoring & Observability

**Error Tracking:**
- None (custom logger implementation)

**Logs:**
- Custom logger: `logger.py`
- Log directory: `logs/`
- Format: Timestamped files per session
- Log levels: INFO, ERROR, SUCCESS, WARNING
- Stack traces captured for errors

## CI/CD & Deployment

**Hosting:**
- Self-hosted (FastAPI + Uvicorn)
- Static SPA served from `admin/dist/`

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- None required (uses JSON config file)

**Secrets location:**
- `config/lively_config.json` (contains API keys - NOT committed to git)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Scheduled Task System

**Scheduler:**
- APScheduler 3.11.2 with AsyncIOScheduler
- Job store: Memory (not persistent)
- Configuration in `scheduler_tasks.py`

**Task Types:**
1. **Parse Tasks** - Analyze novel text and extract roles via AI
2. **Generate Tasks** - Generate audio for novel chapters
3. **Multithread Generate Tasks** - Parallel audio generation
4. **Watchdog Tasks** - Monitor and reload VoxCPM model on failure

**Task Management:**
- Managed via `ScheduledTask` database model
- CRUD operations exposed through `/scheduled-tasks/*` API endpoints
- Task status tracking with locks to prevent concurrent execution
- Cron-based scheduling support

**Background Job Dependencies:**
- VoxCPM model must be loaded in memory
- Database connection required
- API key for Anthropic/MiniMax API

---

*Integration audit: 2026-03-30*
