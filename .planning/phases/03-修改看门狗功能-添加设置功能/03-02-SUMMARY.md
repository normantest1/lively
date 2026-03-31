---
phase: 03-修改看门狗功能-添加设置功能
plan: 02
subsystem: Watchdog Settings
tags: [watchdog, settings, config, frontend]
dependency_graph:
  requires: []
  provides: []
  affects: [scheduler_tasks.py, SettingsView.vue]
tech_stack:
  added: []
  patterns: [config-driven watchdog parameters]
key_files:
  created: []
  modified:
    - admin/src/views/SettingsView.vue
    - scheduler_tasks.py
decisions: []
metrics:
  duration: 318
  completed: 2026-03-31T05:48:44Z
---

# Phase 03 Plan 02 Summary: Watchdog Settings UI and Config-Driven Parameters

## One-Liner

Added watchdog settings UI to SettingsView.vue with RTF threshold, wait times, and auto-recovery switch, and updated scheduler_tasks.py to read all watchdog parameters from config instead of hardcoded values.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add watchdog settings section to SettingsView.vue | 6aa9373 | admin/src/views/SettingsView.vue |
| 2 | Update scheduler_tasks.py to read RTF threshold from config | 2e51f7f | scheduler_tasks.py |
| 3 | Update wait times in scheduler_tasks.py to read from config | e384114 | scheduler_tasks.py |

## Truths Achieved

- SettingsView.vue displays RTF threshold input (el-input-number, 0-2, step 0.1, precision 2), reload wait input, resume wait input, log check lines input, and auto-recovery switch
- scheduler_tasks.py reads RTF threshold from config/lively_config.json instead of hardcoded 0.8
- scheduler_tasks.py reads wait times from config instead of hardcoded 60 and 120 seconds
- scheduler_tasks.py reads log check lines from config instead of hardcoded 10
- All log messages show dynamic values from config

## Artifacts Produced

| Path | Provides | Contains |
|------|----------|----------|
| admin/src/views/SettingsView.vue | Watchdog settings UI | el-input-number for rtf_threshold, watchdog_reload_wait_seconds, watchdog_resume_wait_seconds, watchdog_log_check_lines; el-switch for watchdog_auto_recovery |
| scheduler_tasks.py | Config-driven watchdog parameters | load_config calls for rtf_threshold, watchdog_log_check_lines, watchdog_reload_wait_seconds, watchdog_resume_wait_seconds |

## Key Links

- SettingsView.vue -> api.py via api.getSettings(), api.saveSettings()
- scheduler_tasks.py -> config/lively_config.json via load_config()

## Deviations from Plan

None - plan executed exactly as written.

## Requirements Met

- UI-WATCHDOG-03: Watchdog settings UI in SettingsView.vue
- UI-WATCHDOG-04: Config-driven watchdog parameters in scheduler_tasks.py

## Commits

- 6aa9373: feat(03-02): add watchdog settings section to SettingsView.vue
- 2e51f7f: feat(03-02): read RTF threshold and log check lines from config
- e384114: feat(03-02): read watchdog wait times from config

## Self-Check: PASSED

- SettingsView.vue has watchdog settings section: VERIFIED
- scheduler_tasks.py reads rtf_threshold from config: VERIFIED
- scheduler_tasks.py reads watchdog_reload_wait_seconds from config: VERIFIED
- scheduler_tasks.py reads watchdog_resume_wait_seconds from config: VERIFIED
- scheduler_tasks.py reads watchdog_log_check_lines from config: VERIFIED
- Commit hashes verified: 6aa9373, 2e51f7f, e384114
