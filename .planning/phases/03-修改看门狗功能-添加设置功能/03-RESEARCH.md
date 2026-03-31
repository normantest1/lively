# Phase 3: 修改看门狗功能/添加设置功能 - Research

**Researched:** 2026-03-31
**Domain:** Watchdog configuration + Settings management (FastAPI + Vue 3 + JSON config)
**Confidence:** HIGH

## Summary

Phase 3 has two distinct components: (1) modifying the watchdog functionality to use configurable parameters instead of hardcoded values, and (2) adding those settings to the existing Settings page.

**Current state:** Settings infrastructure already exists (SettingsView.vue, GET/POST /api/settings endpoints, config/lively_config.json). The watchdog has hardcoded values that should become configurable: RTF threshold (0.8), reload wait (60s), resume wait (120s), and log check lines (10).

**Primary recommendation:** Extend the existing settings system rather than creating a new one. Add watchdog-specific settings to lively_config.json, update scheduler_tasks.py to read from config, and add corresponding form fields to SettingsView.vue.

## Project Constraints (from CLAUDE.md)

- **Tech stack locked:** Python 3.12 + FastAPI + Vue 3
- **Database:** SQLite via Peewee
- **Config:** JSON config file at `config/lively_config.json`
- **Naming:** snake_case for Python modules/functions, PascalCase for Vue components

## User Constraints (from CONTEXT.md)

> No CONTEXT.md exists for Phase 3 yet. This is the initial research phase.

---

## Standard Stack

### Core (already in place)
| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.135.1 | REST API framework |
| Peewee | 4.0.2 | SQLite ORM |
| Vue 3 | 3.4.0 | Frontend framework |
| Element Plus | 2.5.0 | UI component library |
| APScheduler | 3.11.2 | Async task scheduling |
| Axios | 1.6.0 | HTTP client |

### No new dependencies required

---

## Architecture Patterns

### Settings Management Pattern (Already Implemented)

**Config storage:** `config/lively_config.json` — key-value JSON

**Backend read:** `utils/config.py::load_config(path, field)` — dot-notation access via `deep_find()`

**Backend API (api.py:1812-1858):**
- `GET /api/settings` — reads from `config/lively_config.json`
- `POST /api/settings` — merges update into existing JSON file

**Frontend:** `SettingsView.vue` — Element Plus form with `api.getSettings()` / `api.saveSettings()`

### Watchdog Pattern (Already Implemented)

**Task execution:** `scheduler_tasks.py`
- `execute_watchdog_task()` — main entry point (line 1121)
- `execute_multithread_generate_task()` — actual generation with queue (line 725)
- `check_rtf_in_logs()` — parses log files for RTF > threshold (line 1216)
- `handle_high_rtf()` — stops server, waits, reloads, resumes (line 1295)

**State tracking:** `batch_generate_state` dict (line 45-51)

**Cancellation:** `asyncio.Event()` per task type (line 36-39)

---

## Hardcoded Values to Make Configurable

| Location | Value | Purpose |
|----------|-------|---------|
| `scheduler_tasks.py:1269` | `0.8` | RTF threshold |
| `scheduler_tasks.py:1007` | `60` | Reload wait (inside multithread task) |
| `scheduler_tasks.py:1026` | `120` | Resume wait (inside multithread task) |
| `scheduler_tasks.py:1325` | `60` | Reload wait (in handle_high_rtf) |
| `scheduler_tasks.py:1359` | `120` | Resume wait (in handle_high_rtf) |
| `scheduler_tasks.py:1251` | `10` | Log lines to check |

**Total instances:** 6 hardcoded values related to watchdog behavior.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Config storage | Custom database table | Existing JSON file at `config/lively_config.json` |
| Settings UI | New page | Extend existing `SettingsView.vue` |
| Config reading | New loader | Existing `utils/config.py::load_config()` |

**Key insight:** The settings infrastructure already exists. Phase 3 only needs to extend it.

---

## Common Pitfalls

### Pitfall 1: Config not reloaded after save
**What goes wrong:** Changes to `lively_config.json` are not picked up until server restart.
**Why it happens:** `utils/config.py::load_config()` reads file on each call, but modules cache values in globals at import time.
**How to avoid:** Use `load_config()` at runtime (not module-level caching) for watchdog parameters.

### Pitfall 2: Conflicting hardcoded defaults vs config values
**What goes wrong:** Module-level defaults differ from config file defaults.
**Why it happens:** `scheduler_tasks.py` imports `load_config` but may use fallback values if config key missing.
**How to avoid:** Ensure config file has all watchdog keys with sensible defaults.

### Pitfall 3: Type coercion issues
**What goes wrong:** JSON number (0.8) treated as string depending on context.
**Why it happens:** Python `json.load()` returns float, but form input may pass string.
**How to avoid:** Explicit type conversion in `load_config` or validation in Pydantic model.

---

## Code Examples

### Reading config at runtime (not import time)
```python
# scheduler_tasks.py
from utils.config import load_config

async def check_rtf_in_logs(log_callback=None) -> bool:
    config_path = Path(__file__).resolve().parent.parent / "config/lively_config.json"
    rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8
    # ... use rtf_threshold instead of hardcoded 0.8
```

### Config field addition to SettingsRequest (api.py:1786)
```python
class SettingsRequest(BaseModel):
    # ... existing fields ...
    rtf_threshold: Optional[float] = None
    watchdog_reload_wait_seconds: Optional[int] = None
    watchdog_resume_wait_seconds: Optional[int] = None
    watchdog_log_check_lines: Optional[int] = None
```

### SettingsView.vue form extension
```vue
<el-divider content-position="left">看门狗设置</el-divider>

<el-form-item label="RTF 阈值" prop="rtf_threshold">
  <el-input-number
    v-model="formData.rtf_threshold"
    :min="0.1"
    :max="1"
    :step="0.1"
    :precision="2"
    style="width: 100%"
  />
</el-form-item>

<el-form-item label="模型重载等待(秒)" prop="watchdog_reload_wait_seconds">
  <el-input-number
    v-model="formData.watchdog_reload_wait_seconds"
    :min="10"
    :max="300"
    :step="10"
    style="width: 100%"
  />
</el-form-item>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed |
|--------------|------------------|--------------|
| Hardcoded RTF 0.8 | Config-driven RTF threshold | Phase 3 |
| Hardcoded 60s/120s waits | Config-driven wait times | Phase 3 |
| Hardcoded 10 log lines | Config-driven log lines | Phase 3 |

**No deprecations in this phase.**

---

## Open Questions

1. **Should watchdog settings be a separate section or part of existing form?**
   - Recommendation: Add as a new `el-divider` section "看门狗设置" within existing SettingsView.vue

2. **Should changes to watchdog settings take effect immediately or require restart?**
   - Current code reads config at runtime via `load_config()`, so no restart needed
   - However, running tasks use values captured at task start

3. **Should there be per-novel watchdog settings or global?**
   - Current watchdog is per-novel (job_id includes novel_name)
   - Settings should be global (all watchdog tasks share same thresholds)

---

## Environment Availability

> SKIPPED — no external dependencies identified. This is a code/config-only change.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None (manual verification) |
| Config file | `config/lively_config.json` |

### Phase Requirements Map
| Req ID | Behavior | Test Type | Verification |
|--------|----------|-----------|--------------|
| TBD | RTF threshold configurable | Manual | Edit config, trigger watchdog, verify behavior |
| TBD | Wait times configurable | Manual | Edit config, trigger high RTF, verify timing |
| TBD | Settings persist in UI | Manual | Save via SettingsView, verify JSON updated |

---

## Sources

### Primary (HIGH confidence)
- `scheduler_tasks.py` — watchdog implementation (lines 1121-1373)
- `api.py` — settings endpoints (lines 1781-1858)
- `utils/config.py` — config loading
- `SettingsView.vue` — existing settings UI

### Secondary (MEDIUM confidence)
- Phase 2 verification document — confirms RTF handling flow

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies needed
- Architecture: HIGH — extends existing settings pattern
- Pitfalls: MEDIUM — config caching behavior needs verification

**Research date:** 2026-03-31
**Valid until:** 90 days (stable pattern, no fast-moving tech)
