# Codebase Concerns

**Analysis Date:** 2026-03-30

## Security Considerations

**API Keys in Plain Text Config:**
- Issue: `config/lively_config.json` stores API key in plain text
- Files: `config/lively_config.json`
- Impact: If config file is committed to git or accessed by unauthorized users, API credentials are compromised
- Fix approach: Use environment variables for secrets, never store credentials in version-controlled files

**CORS Wide Open:**
- Issue: CORS allows all origins (`allow_origins=["*"]`)
- Files: `api.py:2107-2113`
- Impact: Any website can make requests to the API
- Fix approach: Restrict to specific frontend domain in production

**No Authentication:**
- Issue: All API endpoints are publicly accessible with no authentication middleware
- Files: `api.py` (all endpoints)
- Impact: Anyone can create/delete novels, roles, trigger audio generation
- Fix approach: Add authentication (JWT, session-based, or API key)

**Path Traversal Risk in Audio Endpoint:**
- Issue: `get_audio_file` endpoint accepts file path and only checks if file exists after URL decoding and path normalization
- Files: `api.py:1186-1257`
- Impact: Could potentially access files outside the intended audio directory via `../` traversal
- Code:
```python
file_path = unquote(file_path)
file_path = file_path.replace('/', '\\')
if not os.path.exists(file_path):
    raise HTTPException(...)
```
- Fix approach: Validate the decoded path stays within allowed directory using `Path.resolve()` and containment check

**No Input Validation:**
- Issue: Many endpoints accept user input without thorough validation
- Files: `api.py` (Pydantic models have some validation but not comprehensive)
- Impact: Malformed data could cause crashes or unexpected behavior
- Fix approach: Add comprehensive input sanitization

---

## Performance Considerations

**Global Lock on Audio Processing:**
- Issue: `remove_silence_lock = threading.Lock()` in `generate_audio.py` serializes all audio processing
- Files: `generate_audio.py:30`
- Impact: Multi-threaded audio processing cannot run in parallel
- Fix approach: Use finer-grained locking or process-level isolation

**Database Synchronous Mode:**
- Issue: `synchronous=0` in SQLite pragmas disables durability for speed
- Files: `bean/beans.py:16`
- Code:
```python
'synchronous': 0  # 平衡性能和数据安全
```
- Impact: Data loss risk on crash or power failure
- Fix approach: Use `synchronous=1` or `2` for safety, or use a production database

**Inefficient Novel Stats Calculation:**
- Issue: Novel chapter count calculated via `last_novel.id - first_novel.id + 1` which assumes consecutive IDs with no gaps
- Files: `api.py:1035`
- Code:
```python
stored_chapter_count = last_novel.id - first_novel.id + 1
```
- Impact: Incorrect stats if novels are deleted or IDs have gaps
- Fix approach: Use `Novel.select().where(Novel.novel_name == novel_name).count()`

**Large Batch Processing:**
- Issue: `batch_generate_novel` loads all novels into memory via `list(novels)`
- Files: `api.py:627`
- Impact: Memory exhaustion with large chapter counts
- Fix approach: Use generators/chunked processing

**No Connection Pooling:**
- Issue: Peewee creates new connection per query in some configurations
- Files: `bean/beans.py`
- Impact: Performance degradation under concurrent load
- Fix approach: Configure proper connection pooling

---

## Scalability Concerns

**Global Mutable State:**
- Issue: Task running flags, server instance stored as module-level globals
- Files: `scheduler_tasks.py:28-42`, `api.py:169`
- Code:
```python
parse_task_running = False
generate_task_running = False
server = ""
```
- Impact: Cannot scale horizontally, difficult to debug state issues
- Fix approach: Use proper state management (database, Redis, or class-based)

**MemoryJobStore Not Persistent:**
- Issue: APScheduler uses in-memory storage
- Files: `scheduler_tasks.py:19-26`
- Code:
```python
scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
```
- Impact: Scheduled tasks lost on restart
- Fix approach: Use persistent job store (SQLAlchemy, Redis)

**Single GPU Assumption:**
- Issue: Hardcoded `devices=[0]` for VoxCPM model
- Files: `api.py:201`
- Impact: Cannot utilize multiple GPUs or different device configurations
- Fix approach: Make device selection configurable

**Watchdog Task Restarts Server:**
- Issue: Watchdog calls `server.stop()` and reloads model on high RTF
- Files: `scheduler_tasks.py:962`
- Impact: Blocks all operations during restart, no high availability
- Fix approach: Implement graceful rolling updates or queue-based load distribution

---

## Known Technical Debt

**Duplicate Split Functions:**
- Issue: Three near-identical functions for splitting novels
- Files: `api.py:44,248,354`
- Functions: `split_novel_text`, `split_novel_text2`, `split_novel_text_by_content_list`
- Impact: Code duplication, maintenance burden
- Fix approach: Consolidate into single parameterized function

**Undefined Model Field:**
- Issue: Role model gets `type` attribute set but field not defined in model
- Files: `parse_text.py:876`
- Code:
```python
role = Role(
    role_name="BUG角色",
    ...
    type=_type,  # This field doesn't exist in Role model!
```
- Impact: AttributeError if this code path is hit (though it may never be triggered in practice)
- Fix approach: Add `type` field to Role model or remove this code

**TODO Comments Not Addressed:**
- Issue: Several TODO comments indicate known issues
- Files: `api.py:13`, `parse_text.py:621`, `utils/common.py:456`
- TODOs:
  - `api.py:13`: "TODO 这里是关键注释" (unclear what this refers to)
  - `parse_text.py:621`: "TODO 这里需要修改成按照传进来的小说名字和分析数量进行运行"
  - `utils/common.py:456`: "TODO 添加数据时，得判断小说名是否存在"

**Undocumented API Contract:**
- Issue: Comment shows assumed data structure for `chapter_role_list`
- Files: `generate_audio.py:521-528`
- Code:
```python
"""
这里假设传入的chapter_role_list列表是[{
"role_name": "张三",
"type": "narration或role",
"bind_role_audio_name": "素琴",
"text":"小说内容"
}]
"""
```
- Impact: API consumer must guess expected format
- Fix approach: Document with TypeScript interfaces or JSON schema

**Debug Code in Production:**
- Issue: Extensive debug logging with emoji and diagnostic messages
- Files: `generate_audio.py:431,579`, `scheduler_tasks.py`
- Impact: Log spam, potential performance impact
- Fix approach: Use proper log levels (DEBUG vs INFO)

---

## Error Handling Gaps

**Bare json.loads Without Try-Catch:**
- Issue: JSON parsing in `model_parse` can crash on invalid response
- Files: `api.py:173`
- Code:
```python
return json.loads(full_response_text)
```
- Impact: API returns 500 if LLM returns malformed JSON
- Fix approach: Wrap in try-except with retry or error response

**Bare except Blocks:**
- Issue: Several places use bare `except Exception` without specific handling
- Files: Multiple files
- Impact: Silent failures or cryptic error messages
- Fix approach: Catch specific exceptions with appropriate recovery

**No API Retry Logic:**
- Issue: LLM API calls fail without retry on transient errors
- Files: `api.py:146-173`, `parse_text.py:175-237`
- Impact: One network blip fails entire batch
- Fix approach: Implement exponential backoff retry

**Transaction Rollback Issues:**
- Issue: Some error paths call `get_db().rollback()` but database might not be in a transaction
- Files: `api.py:142,246,351`
- Impact: Error if rollback called without active transaction
- Fix approach: Check `db.get_autocommit()` state before rollback

**Missing NULL Checks:**
- Issue: Direct access to fields without null checks
- Files: Multiple files
- Impact: AttributeError if data is unexpectedly null
- Fix approach: Use optional chaining / null checks

---

## Test Coverage Gaps

**No Test Files Found:**
- Issue: No test files detected in codebase
- Files: No `test_*.py`, `*_test.py`, or `pytest.ini` found
- Impact: No automated verification of functionality
- Fix approach: Add pytest with unit and integration tests

**No Frontend Tests:**
- Issue: No Vue test setup detected
- Files: No `jest.config.*`, `vitest.config.*` in admin folder
- Impact: UI changes cannot be automatically validated
- Fix approach: Add Vitest for component testing

---

## Dependency Risks

**Outdated Dependencies:**
- Issue: Vue 3.4.0, Element Plus 2.5.0 are older versions
- Files: `admin/package.json`
- Impact: Known vulnerabilities in older versions
- Fix approach: Update to latest stable versions

**Missing Lock File:**
- Issue: `admin/package-lock.json` not checked (may be in .gitignore)
- Files: `admin/package.json`
- Impact: Non-deterministic installs
- Fix approach: Commit lock file

**Large Node Modules:**
- Issue: `admin/node_modules` contains many nested dependencies
- Impact: Repository bloat, slow CI/CD
- Fix approach: Use `.npmrc` with proper cache settings, consider pnpm

---

## Compliance Considerations

**No Audit Logging:**
- Issue: No structured audit trail for data modifications
- Impact: Cannot trace who changed what and when
- Fix approach: Add audit log table or use existing logging infrastructure

**No Data Backup Strategy:**
- Issue: SQLite database with WAL mode but no documented backup
- Files: `bean/beans.py`
- Impact: Data loss risk
- Fix approach: Implement regular backup schedule

**Hardcoded Paths:**
- Issue: Many paths use absolute paths or relative paths that break on different systems
- Files: `api.py:8`, `generate_audio.py:15-16`, `parse_text.py:10-11`
- Impact: Only works in specific development environment
- Fix approach: Use environment variables or Path resolution from project root

---

*Concerns audit: 2026-03-30*
