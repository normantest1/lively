<!-- GSD:project-start source:PROJECT.md -->
## Project

**Lively - 有声书生成系统**

一个有声书生成系统，用户上传小说文本，系统通过 AI 分析提取角色对话，将角色绑定音频后使用 VoxCPM 模型生成语音片段，最终合成为完整有声书。

**Core Value:** 将小说文本自动转换为角色配音的有声书

### Constraints

- **技术栈锁定**: Python 3.12 + FastAPI + Vue 3 — 不得更换
- **数据库**: SQLite — 暂不迁移到其他数据库
- **GPU 要求**: VoxCPM 需要 CUDA GPU — 部署环境必须满足
- **API 依赖**: 需要 MiniMax API Key — 必须配置
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Backend API, audio processing, text parsing, scheduled tasks
- JavaScript/TypeScript - Frontend admin panel
- Vue 3 (Composition API) - Frontend UI framework
## Runtime
- Python 3.12 with CUDA 12.8 (GPU acceleration for audio generation)
- Node.js (for frontend build)
- pip (Python dependencies)
- npm (Node.js dependencies)
- Lockfile: `requirements.txt`
## Frameworks
- FastAPI 0.135.1 - REST API framework
- Starlette 0.52.1 - ASGI framework (FastAPI dependency)
- Uvicorn 0.42.0 - ASGI server
- Vue 3.4.0 - Progressive JavaScript framework
- Vue Router 4.2.5 - SPA routing
- Element Plus 2.5.0 - UI component library
- Axios 1.6.0 - HTTP client
- Peewee 4.0.2 - Lightweight ORM
- SQLite - Database engine (via Peewee)
- torch 2.10.0+cu128 - PyTorch with CUDA
- torchaudio 2.10.0+cu128 - Audio processing
- nano-vllm-voxcpm 1.0.1 - VoxCPM model serving
- transformers 5.3.0 - Hugging Face transformers
- APScheduler 3.11.2 - AsyncIOScheduler for background jobs
- pydub 0.25.1 - Audio manipulation
- soundfile 0.13.1 - Audio file I/O
- Not detected
- Vite 5.0.0 - Frontend build tool
- @vitejs/plugin-vue 5.0.0 - Vue support for Vite
## Key Dependencies
- fastapi 0.135.1 - API framework
- pydantic 2.12.5 - Data validation
- peewee 4.0.2 - Database ORM
- anthropic 0.86.0 - Claude API client
- pydub 0.25.1 - Audio processing
- torch 2.10.0+cu128 - Deep learning framework
- uvicorn 0.42.0 - ASGI server
- APScheduler 3.11.2 - Job scheduling
- python-multipart 0.0.22 - File upload support
- python-dateutil 2.9.0 - Date utilities
## Configuration
- JSON config file: `config/lively_config.json`
- Configuration fields:
- `admin/vite.config.js` - Vite configuration for frontend
- Base path: `./` (for SPA deployment)
- Output: `admin/dist/`
## Platform Requirements
- Python 3.12+
- Node.js 18+
- CUDA-compatible GPU (for VoxCPM audio generation)
- Windows or Linux
- FastAPI application served via Uvicorn
- Static files served from `admin/dist/`
- SQLite database (file-based)
- GPU required for audio generation
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
### Python Backend
- Python modules: `snake_case.py` (e.g., `parse_text.py`, `generate_audio.py`, `scheduler_tasks.py`)
- Database models: `snake_case.py` (e.g., `bean/beans.py`)
- snake_case (e.g., `load_config`, `get_novel_name`, `split_novel_text`)
- Private functions prefixed with underscore: `_add_to_logs`, `_get_db`
- snake_case (e.g., `novel_name`, `chapter_count`, `role_audio_id`)
- Global variables uppercase: `ROOT_DIR`, `config_path`
- Boolean variables often use `is_` prefix: `is_bind`, `is_active`
- PascalCase (e.g., `BaseModel`, `ConnectionManager`, `DynamicConcurrentProcessor`)
- snake_case table names via `Meta.table_name` (e.g., `novels`, `roles`, `role_audios`)
### Frontend (Vue/JS)
- Vue components: PascalCase (e.g., `NovelManage.vue`, `RoleAudioManage.vue`)
- JavaScript modules: camelCase or snake_case in API layer
- API functions: camelCase (e.g., `getNovels`, `createRole`, `batchGenerateNovel`)
- Template uses kebab-case for attributes (e.g., `el-button`, `el-input`)
- Script uses camelCase for methods and variables
## Code Organization
### Python Backend
## Error Handling
### Python Backend
### Frontend (Vue)
## Logging Conventions
### Backend Python Logging
- `init_logger()`: Creates timestamped log file in `logs/` directory
- `log(message)`: Writes message to both stdout and log file
- `log_error(message)`: Writes error with full stack trace
- `close_logger()`: Closes log file on shutdown
### Frontend Logging
- No dedicated logging framework
- Uses `console.log` for debugging (in dist files only)
- User-facing errors via `ElMessage.error()`
## Linting and Formatting
### Python
- No `.pylintrc`, `pyproject.toml`, `setup.cfg`, or `setup.py` with lint config
- No pre-commit hooks
- No automated formatting (black, ruff, etc.)
- 4-space indentation standard
- Chinese comments in code
- Mix of early returns and if-else blocks
- Some functions are very long (e.g., `api.py` has 2000+ lines)
### Frontend (Vue/JS)
- No `.eslintrc`, `.eslintrc.js`, `eslint.config.js`
- No `.prettierrc` or `.prettierrc.js`
## Comments
## Function Design
- Positional args for required values
- Keyword args with defaults for optional configuration
- API endpoints return Pydantic models or HTTPExceptions
- Processing functions return boolean (success/failure)
- Query functions return model instances or `None`
- Batch operations return summary dictionaries
## Module Design
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- FastAPI REST API backend serving both data and static frontend files
- SQLite database with Peewee ORM for persistence
- AI-powered text analysis pipeline using Claude API (MiniMax)
- VoxCPM local model for audio generation
- APScheduler for async task scheduling
- Vue 3 SPA frontend with Element Plus UI
- WebSocket support for real-time log streaming
## Layers
- Purpose: REST API endpoints and application lifecycle
- Location: `D:/Projects/Python/lively/api.py`
- Contains: FastAPI app, Pydantic models, all route handlers
- Depends on: bean, utils, scheduler_tasks, generate_audio, parse_text
- Used by: Vue.js frontend via axios
- Purpose: Database models and ORM definitions
- Location: `D:/Projects/Python/lively/bean/beans.py`
- Contains: Novel, Role, NovelName, RoleAudio, ScheduledTask models
- Depends on: peewee, config
- Used by: api.py, parse_text.py, generate_audio.py, scheduler_tasks.py
- Purpose: Novel text parsing and AI analysis
- Location: `D:/Projects/Python/lively/parse_text.py`
- Contains: Chapter segmentation, AI prompt construction, dialogue extraction
- Depends on: bean, utils.config, anthropic client
- Used by: api.py, scheduler_tasks.py
- Purpose: Audio generation and silence removal
- Location: `D:/Projects/Python/lively/generate_audio.py`
- Contains: VoxCPM integration, audio segment processing, role audio loading
- Depends on: bean, utils.config, VoxCPM
- Used by: api.py, scheduler_tasks.py
- Purpose: Background task management with APScheduler
- Location: `D:/Projects/Python/lively/scheduler_tasks.py`
- Contains: Job management, task status tracking, cron scheduling
- Depends on: apscheduler, bean
- Used by: api.py
- Purpose: Configuration loading from JSON
- Location: `D:/Projects/Python/lively/utils/config.py`
- Contains: JSON config reader with dot-notation access
- Used by: All modules
- Purpose: Dual-output logging (console + file)
- Location: `D:/Projects/Python/lively/logger.py`
- Contains: Timestamp-based log files in `logs/` directory
- Used by: All modules
- Purpose: Vue.js admin interface
- Location: `D:/Projects/Python/lively/admin/`
- Contains: Vue 3 SPA with Vue Router, Element Plus
- Entry: `admin/src/main.js`
## Data Flow
```
```
```
```
## Key Abstractions
- State 1: `已分片待解析` (Segmented, pending AI analysis)
- State 2: `已解析待合成` (Analyzed, pending audio synthesis)
- State 3: `已合成语音` (Synthesized, audio complete)
- `Role.is_bind` indicates if character has associated audio
- `Role.bind_audio_name` references `RoleAudio.role_name`
- `RoleAudio.citation_count` tracks usage frequency
- Types: `parse`, `generate`, `multithread-generate`, `watchdog`
- Managed via `ScheduledTask` model and APScheduler
- Support cron expressions for scheduling
## Entry Points
- Location: `D:/Projects/Python/lively/api.py`
- Triggers: `uvicorn api:app` or `python api.py`
- Port: 6888
- Responsibilities: API routes, CORS, static file serving, lifespan management
- Location: `D:/Projects/Python/lively/bean/beans.py`
- Trigger: Module import at startup
- Creates tables if not exist: `novels`, `roles`, `novel_names`, `role_audios`, `scheduled_tasks`
- Location: `D:/Projects/Python/lively/admin/`
- Build output: `D:/Projects/Python/lively/admin/dist/`
- Served by FastAPI at `/` and `/assets/`
## Error Handling
- `try/except` blocks with `traceback.print_exc()` and `log_error()`
- `HTTPException` with status codes for API errors
- Database rollback on failure via `db.rollback()`
- Global exception handlers at API endpoints
## Cross-Cutting Concerns
- Files stored in `logs/` with timestamp naming
- Separate `log()`, `log_error()`, `log_success()`, `log_warning()` functions
- `NovelBase`, `RoleBase`, `NovelNameBase`, `RoleAudioBase` for creation
- `*Update` models with Optional fields for partial updates
- `ConfigDict(from_attributes=True)` for ORM-to-Pydantic conversion
- Database name, API keys, model parameters, token limits
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
