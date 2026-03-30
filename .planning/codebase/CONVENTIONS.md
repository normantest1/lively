# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

### Python Backend

**Files:**
- Python modules: `snake_case.py` (e.g., `parse_text.py`, `generate_audio.py`, `scheduler_tasks.py`)
- Database models: `snake_case.py` (e.g., `bean/beans.py`)

**Functions:**
- snake_case (e.g., `load_config`, `get_novel_name`, `split_novel_text`)
- Private functions prefixed with underscore: `_add_to_logs`, `_get_db`

**Variables:**
- snake_case (e.g., `novel_name`, `chapter_count`, `role_audio_id`)
- Global variables uppercase: `ROOT_DIR`, `config_path`
- Boolean variables often use `is_` prefix: `is_bind`, `is_active`

**Classes:**
- PascalCase (e.g., `BaseModel`, `ConnectionManager`, `DynamicConcurrentProcessor`)

**Database Tables:**
- snake_case table names via `Meta.table_name` (e.g., `novels`, `roles`, `role_audios`)

### Frontend (Vue/JS)

**Files:**
- Vue components: PascalCase (e.g., `NovelManage.vue`, `RoleAudioManage.vue`)
- JavaScript modules: camelCase or snake_case in API layer
- API functions: camelCase (e.g., `getNovels`, `createRole`, `batchGenerateNovel`)

**Vue Components:**
- Template uses kebab-case for attributes (e.g., `el-button`, `el-input`)
- Script uses camelCase for methods and variables

## Code Organization

### Python Backend

**Directory Structure:**
```
D:/Projects/Python/lively/
├── api.py                 # FastAPI application with all REST endpoints
├── bean/
│   └── beans.py           # Peewee ORM models (Novel, Role, NovelName, RoleAudio, ScheduledTask)
├── utils/
│   ├── config.py          # Configuration loading utilities
│   └── common.py          # Shared utilities (split_novel_text, array_to_obj_list)
├── logger.py              # Custom logging module
├── generate_audio.py      # Audio generation logic
├── parse_text.py          # Text parsing and AI integration
├── scheduler_tasks.py      # APScheduler task management
└── config/
    └── lively_config.json # Runtime configuration
```

**Import Organization (api.py):**
```python
# Standard library
import json, os, datetime, traceback

# Third-party
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Query, UploadFile, WebSocket
from peewee import *

# Local imports
from bean.beans import RoleAudio, Role, Novel, get_db, NovelName
from logger import init_logger, log, log_error, close_logger
from generate_audio import update_audio_role, load_role_audio, generate_chapter_audio
from parse_text import async_parse_text, parse_novel_data_bind_role_audio
from scheduler_tasks import (add_parse_job, add_generate_job, ...)
```

**Frontend Structure:**
```
admin/src/
├── api/
│   └── index.js           # Axios API client with all endpoints
├── views/
│   ├── NovelManage.vue    # Novel CRUD view
│   ├── RoleManage.vue     # Role management view
│   ├── RoleAudioManage.vue
│   ├── SettingsView.vue
│   └── ScheduledTaskView.vue
├── router/
├── App.vue
└── main.js
```

## Error Handling

### Python Backend

**Pattern 1: Try/Except with Logging**
```python
# From utils/common.py
try:
    get_db().begin()
    # operations
    db.commit()
except Exception as e:
    print(e)
    logger_log(str(e))
    traceback.print_exc()
    db.rollback()
```

**Pattern 2: HTTPException for API Errors (FastAPI)**
```python
# From api.py
try:
    return Novel.get_by_id(novel_id)
except Novel.DoesNotExist:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Novel with id {novel_id} not found"
    )
except Exception as e:
    log_error(f"获取小说失败 (novel_id={novel_id}): {str(e)}")
    raise
```

**Pattern 3: Custom Error Logging Function**
```python
# From logger.py
def log_error(message: str = None):
    """记录完整的错误信息，包括堆栈跟踪"""
    global _log_file
    if _log_file:
        if message:
            _log_file.write(f"\n{'='*80}\n")
            _log_file.write(f"错误信息: {message}\n")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None:
            traceback.print_exc(file=_log_file)
        _log_file.flush()
```

**Pattern 4: Result Dictionaries for Silent Failures**
```python
# From generate_audio.py
return {
    "success": False,
    "original_duration": 0,
    "processed_duration": 0,
    "removed_duration": 0,
    "removed_count": 0,
    "message": f"处理音频时出错: {str(e)}"
}
```

### Frontend (Vue)

**Axios Interceptor Pattern**
```javascript
// From admin/src/api/index.js
apiClient.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)
```

## Logging Conventions

### Backend Python Logging

**Custom Logger Module** (`logger.py`):
- `init_logger()`: Creates timestamped log file in `logs/` directory
- `log(message)`: Writes message to both stdout and log file
- `log_error(message)`: Writes error with full stack trace
- `close_logger()`: Closes log file on shutdown

**Log File Naming:**
```
logs/{year}年{month}月{day}日{hour}时{minute}分{second}秒服务器启动日志.log
```

**Scheduler Tasks Logging** (`scheduler_tasks.py`):
```python
def log_info(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [INFO] {message}"
    print(log_line)
    logger_log(log_line)

def log_error(message: str = None):
    # Includes full stack trace via sys.exc_info()
```

**Inline Print + Log Pattern:**
```python
print(f"小说 {novel_name} 状态从 {current_state} 修改为 {new_state}")
log(f"小说 {novel_name} 状态从 {current_state} 修改为 {new_state}")
```

### Frontend Logging

**Minimal Frontend Logging:**
- No dedicated logging framework
- Uses `console.log` for debugging (in dist files only)
- User-facing errors via `ElMessage.error()`

## Linting and Formatting

### Python

**No Formal Linting Config Detected:**
- No `.pylintrc`, `pyproject.toml`, `setup.cfg`, or `setup.py` with lint config
- No pre-commit hooks
- No automated formatting (black, ruff, etc.)

**Style Observations:**
- 4-space indentation standard
- Chinese comments in code
- Mix of early returns and if-else blocks
- Some functions are very long (e.g., `api.py` has 2000+ lines)

### Frontend (Vue/JS)

**Build Tool:** Vite 5 with `@vitejs/plugin-vue`

**No ESLint/Prettier Config Detected:**
- No `.eslintrc`, `.eslintrc.js`, `eslint.config.js`
- No `.prettierrc` or `.prettierrc.js`

**Vite Config** (`admin/vite.config.js`):
```javascript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  base: './',
  build: {
    outDir: 'dist',
    minify: 'esbuild'
  }
})
```

## Comments

**Chinese Comments Common:**
```python
# 从 utils/common.py
def split_novel_text(novel_path):
    """
    将分割的小说文本，加上提示词，发送给ai解析
    :return:
    """
```

**TODO Comments:**
```python
# api.py:13
# TODO 这里是关键注释

# utils/common.py:456
# TODO 添加数据时，得判断小说名是否存在

# parse_text.py:621
# TODO 这里需要修改成按照传进来的小说名字和分析数量进行运行
```

**Inline Comments for Clarity:**
```python
# 检查输入文件是否存在
if not os.path.exists(input_path):
    return {...}
```

## Function Design

**Size:** Functions tend to be long (100-200+ lines common)

**Parameters:** Mixed approach:
- Positional args for required values
- Keyword args with defaults for optional configuration

**Return Patterns:**
- API endpoints return Pydantic models or HTTPExceptions
- Processing functions return boolean (success/failure)
- Query functions return model instances or `None`
- Batch operations return summary dictionaries

## Module Design

**Exports:** Direct module-level imports
```python
from bean.beans import Novel, Role, NovelName, get_db, NovelName
```

**No Barrel Files:** Each module exposes what it needs directly

**Database Pattern (Peewee):**
```python
# Singleton database instance
db = init_db()

class BaseModel(Model):
    class Meta:
        database = db

class Novel(BaseModel):
    id = AutoField(primary_key=True)
    novel_name = CharField(max_length=100)
    # ...
```

---

*Convention analysis: 2026-03-30*
