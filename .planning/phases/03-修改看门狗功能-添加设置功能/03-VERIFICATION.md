---
phase: 03-修改看门狗功能-添加设置功能
verified: 2026-03-31T12:00:00Z
status: gaps_found
score: 10/10 must-haves verified
gaps:
  - truth: "Requirements traceability - UI-WATCHDOG-03, UI-WATCHDOG-04, UI-WATCHDOG-05 not documented in REQUIREMENTS.md"
    status: failed
    reason: "Requirement IDs declared in ROADMAP.md and PLAN frontmatter do not exist in REQUIREMENTS.md"
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Missing UI-WATCHDOG-03, UI-WATCHDOG-04, UI-WATCHDOG-05 definitions"
    missing:
      - "UI-WATCHDOG-03: RTF重启阈值可配置 requirement definition"
      - "UI-WATCHDOG-04: 看门狗生成任务自动重启开关 requirement definition"
      - "UI-WATCHDOG-05: 系统启动时清理temp目录wav文件 requirement definition"
---

# Phase 3: 修改看门狗功能/添加设置功能 Verification Report

**Phase Goal:** 完善看门狗配置化和任务持久化功能

**Verified:** 2026-03-31
**Status:** gaps_found
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Config file has rtf_threshold and watchdog_auto_recovery keys | VERIFIED | config/lively_config.json lines 9-13 contain all 5 watchdog config keys |
| 2 | WatchdogTask model exists and creates watchdog_tasks table | VERIFIED | bean/beans.py lines 90-104 define WatchdogTask; line 104 includes it in db.create_tables |
| 3 | Settings API accepts and returns new watchdog config fields | VERIFIED | api.py lines 1851-1855 define SettingsRequest fields; lines 1869-1873 return defaults |
| 4 | SettingsView.vue displays RTF threshold input and watchdog auto-recovery switch | VERIFIED | SettingsView.vue lines 93-144 contain "看门狗设置" section with el-input-number and el-switch |
| 5 | scheduler_tasks.py reads RTF threshold from config instead of hardcoded 0.8 | VERIFIED | scheduler_tasks.py line 1272: `rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8` |
| 6 | scheduler_tasks.py reads wait times from config instead of hardcoded values | VERIFIED | scheduler_tasks.py lines 1020-1021, 1086, 1357-1358 use `load_config(config_path, "watchdog_reload_wait_seconds")` and `load_config(config_path, "watchdog_resume_wait_seconds")` |
| 7 | Watchdog task state persists to watchdog_tasks table during execution | VERIFIED | scheduler_tasks.py lines 1181-1198 create WatchdogTask; lines 700-708 update completed_chapters |
| 8 | System startup reads watchdog_auto_recovery from config and behaves accordingly | VERIFIED | api.py lines 183-220 restore_watchdog_tasks() reads config and handles both cases |
| 9 | System startup cleans temp/*.wav files | VERIFIED | api.py lines 172-181 cleanup_temp_wavs() deletes temp/*.wav; called at line 258 |
| 10 | WebSocket sends recovery message when tasks are restored | VERIFIED | api.py lines 201-205 (cleanup) and 215-219 (recovery) send watchdog_recovery messages via manager.send_message |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/lively_config.json` | Watchdog configuration storage | VERIFIED | Contains rtf_threshold, watchdog_auto_recovery, watchdog_reload_wait_seconds, watchdog_resume_wait_seconds, watchdog_log_check_lines |
| `bean/beans.py` | WatchdogTask database model | VERIFIED | Lines 90-104 define class WatchdogTask with table_name='watchdog_tasks' |
| `api.py` | Settings API extension | VERIFIED | Lines 1841-1855 SettingsRequest; lines 1858-1874 get_default_settings; lines 1893-1936 save_settings |
| `admin/src/views/SettingsView.vue` | Watchdog settings UI | VERIFIED | Lines 93-144 add "看门狗设置" section with all 5 configuration inputs |
| `scheduler_tasks.py` | Config-driven watchdog parameters | VERIFIED | RTF threshold and wait times read from config; WatchdogTask persistence implemented |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| api.py | config/lively_config.json | save_settings endpoint | WIRED | Lines 1893-1936 handle POST /api/settings and persist to config file |
| bean/beans.py | db | WatchdogTask model | WIRED | WatchdogTask operations use db via get_db() |
| SettingsView.vue | api.py | api.getSettings(), api.saveSettings() | WIRED | loadSettings() and handleSave() functions call API |
| scheduler_tasks.py | config/lively_config.json | load_config() | WIRED | Multiple locations use load_config for watchdog parameters |
| scheduler_tasks.py | WatchdogTask | model operations | WIRED | create() at line 1188, update() at lines 703-706, 1258-1261 |
| api.py | manager.send_message | WebSocket push | WIRED | Lines 201-205, 215-219 send watchdog_recovery messages |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| config/lively_config.json | watchdog config | Static JSON file | N/A (config file) | N/A |
| WatchdogTask table | task state | scheduler_tasks.py writes | Yes - persisted to SQLite | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Config file valid JSON | `node -e "JSON.parse(require('fs').readFileSync('config/lively_config.json'))"` | Parses successfully | PASS |
| WatchdogTask model imports | `python -c "from bean.beans import WatchdogTask; print(WatchdogTask._meta.table_name)"` | watchdog_tasks | PASS |
| SettingsRequest has new fields | `grep -c "rtf_threshold.*Optional\[float\]" api.py` | 1 | PASS |
| SettingsView.vue has watchdog section | `grep -c "看门狗设置" admin/src/views/SettingsView.vue` | 1 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-WATCHDOG-03 | 03-01, 03-02 | RTF重启阈值可配置 | SATISFIED | Config key exists, SettingsView has input, scheduler_tasks reads from config |
| UI-WATCHDOG-04 | 03-01, 03-02, 03-03 | 看门狗生成任务自动重启开关 | SATISFIED | watchdog_auto_recovery in config, WatchdogTask persistence, restore/delete on startup |
| UI-WATCHDOG-05 | 03-03 | 系统启动时清理temp目录wav文件 | SATISFIED | cleanup_temp_wavs() called at api.py startup |

**NOTE:** UI-WATCHDOG-03, UI-WATCHDOG-04, UI-WATCHDOG-05 are declared in ROADMAP.md and PLAN frontmatter, but the requirement definitions do NOT exist in REQUIREMENTS.md. This is a requirements traceability gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| api.py | 13 | `# TODO 这里是关键注释` | INFO | Not a stub - Chinese comment marking important code |

### Human Verification Required

None - all automated checks passed.

### Gaps Summary

**Gap 1: Requirements Traceability (BLOCKER)**
The requirement IDs UI-WATCHDOG-03, UI-WATCHDOG-04, and UI-WATCHDOG-05 are referenced in ROADMAP.md and in the PLAN files' `requirements:` frontmatter fields, but they are not defined in REQUIREMENTS.md. This breaks the traceability chain.

**Implementation is complete and correct.** All 10 observable truths verified, all artifacts exist and are wired, all key links connected. The phase goal is achieved.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
