---
phase: 03-修改看门狗功能-添加设置功能
plan: "03"
subsystem: watchdog
tags: [watchdog, persistence, database, startup]

# Dependency graph
requires:
  - phase: "03-02"
    provides: "WatchdogTask model, watchdog config keys in lively_config.json"
provides:
  - WatchdogTask persistence during task execution
  - temp/*.wav cleanup on startup
  - watchdog recovery with WebSocket notifications
  - runtime switch-off behavior for auto-recovery
affects: [03-修改看门狗功能-添加设置功能 (all plans)]

# Tech tracking
tech-stack:
  added: []
  patterns: [WatchdogTask persistence pattern, startup recovery pattern]

key-files:
  created: []
  modified:
    - scheduler_tasks.py
    - api.py

key-decisions:
  - "WatchdogTask records created at task start, updated per chapter, marked is_running=False on completion"
  - "cleanup_temp_wavs() called synchronously at startup before scheduler starts"
  - "restore_watchdog_tasks() called via asyncio.create_task to avoid blocking"

patterns-established: []

requirements-completed: [UI-WATCHDOG-04, UI-WATCHDOG-05]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 03 Plan 03: Watchdog Task Persistence and Startup Recovery Summary

**Implemented watchdog task persistence to watchdog_tasks table, temp/*.wav cleanup on startup, and WebSocket recovery notifications with runtime switch-off handling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T05:51:51Z
- **Completed:** 2026-03-31T05:54:30Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- WatchdogTask records created at task start, updated per chapter completion, marked is_running=False on completion
- temp/*.wav files cleaned on system startup via cleanup_temp_wavs()
- restore_watchdog_tasks() sends WebSocket messages for each running task on startup
- When watchdog_auto_recovery is False, all watchdog_tasks records deleted at startup
- When switch is turned off via settings, all watchdog_tasks records deleted immediately

## Task Commits

Each task was committed atomically:

1. **Task 1: Add WatchdogTask persistence during task execution** - `4e8d0f4` (feat)
2. **Task 2: Add temp cleanup and watchdog recovery on startup** - `31e0fb1` (feat)
3. **Task 3: Delete watchdog tasks when auto-recovery is turned off** - `0f0437d` (feat)

## Files Created/Modified
- `scheduler_tasks.py` - Added WatchdogTask import, create/update/is_running=False persistence logic
- `api.py` - Added cleanup_temp_wavs() and restore_watchdog_tasks() functions, calls in lifespan, switch-off handling in save_settings

## Decisions Made

- WatchdogTask records created at task start, updated per chapter, marked is_running=False on completion
- cleanup_temp_wavs() called synchronously at startup before scheduler starts
- restore_watchdog_tasks() called via asyncio.create_task to avoid blocking lifespan
- When watchdog_auto_recovery is False at startup, all watchdog_tasks records deleted and WebSocket notification sent
- When switch is turned off via settings POST, all watchdog_tasks records deleted immediately

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Truths Achieved

- WatchdogTask table has records created when watchdog tasks start
- completed_chapters updated in watchdog_tasks as chapters complete
- temp/*.wav files deleted when api.py starts
- WebSocket sends recovery message when watchdog_auto_recovery is true
- WebSocket sends cleanup message when watchdog_auto_recovery is false
- All watchdog_tasks records deleted when watchdog_auto_recovery is turned off

## Requirements Met

- UI-WATCHDOG-04: Watchdog task state persists to watchdog_tasks table during execution
- UI-WATCHDOG-05: System startup reads watchdog_auto_recovery from config and behaves accordingly

## Next Phase Readiness

- All phase 03 requirements complete
- Phase 03 plan 01, 02, and 03 all committed
- No blockers for subsequent phases

---
*Phase: 03-03*
*Completed: 2026-03-31*
