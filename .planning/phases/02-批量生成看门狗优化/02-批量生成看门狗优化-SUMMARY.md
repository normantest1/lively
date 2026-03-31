# Phase 02 Plan 01: 修改看门狗任务执行逻辑 Summary

## Overview

**Plan:** 02-批量生成看门狗优化
**Objective:** 修改看门狗任务逻辑，实现添加时立即执行生成、Cron触发只检查RTF、RTF>0.8时自动处理

## One-liner

Implemented watchdog task execution logic: immediate generation on add, RTF-only cron check, and auto-recovery when RTF>0.8

## Commits

| Task | Description | Hash |
|------|-------------|------|
| 1 | Add batch_generate_state tracking variable | e32ad3a |
| 2 | Execute watchdog task immediately on add | fd4622a |
| 3 | Separate RTF check from generation | 4ed08a7 |
| 4 | Add handle_high_rtf function | a23e815 |
| 5 | Add state tracking to multi-thread generate | fa8e747 |

## Changes Made

### scheduler_tasks.py

**Task 1: Add batch_generate_state tracking variable**
- Added `batch_generate_state` dict with keys: `threads`, `total_chapters`, `completed_chapters`, `is_paused`, `is_stopping`
- State initialized at start of `execute_multithread_generate_task`

**Task 2: Execute watchdog task immediately on add**
- Modified `add_watchdog_job` to use `asyncio.get_event_loop().create_task()` for immediate fire-and-forget execution
- Cron trigger stored with empty values so it only checks RTF

**Task 3: Separate RTF check from generation**
- Cron trigger now passes empty `novel_name` and `chapter_count=0` to scheduler
- Immediate execution uses real values for generation + RTF check
- Cron trigger only performs RTF check

**Task 4: Add handle_high_rtf function**
- New async function `handle_high_rtf(log_callback)` handles RTF>0.8 scenario:
  1. Mark task as paused/stopping
  2. Stop VoxCPM server
  3. Wait 60 seconds
  4. Reload VoxCPM model
  5. Wait 120 seconds
  6. Resume task
- Modified `execute_watchdog_task` to call `handle_high_rtf` when RTF>0.8

**Task 5: Add state tracking to multi-thread generate**
- `execute_single_chapter_from_queue` updates `batch_generate_state['completed_chapters']` after each successful chapter
- `execute_multithread_generate_task` checks `is_paused`/`is_stopping` before starting workers

## Deviations from Plan

None - all tasks executed as specified.

## Verification

- All 5 tasks committed individually
- grep confirms key patterns present:
  - `batch_generate_state` defined and used
  - `立即开始执行批量生成任务` logged on add
  - `RTF 检查正常` logged when RTF OK
  - `handle_high_rtf` function defined and called
  - `completed_chapters += 1` after chapter completion
  - `任务已暂停，等待恢复` check before worker start

## Metrics

- **Duration:** ~execution time
- **Files Modified:** 1 (scheduler_tasks.py)
- **Lines Added:** ~110
- **Tasks Completed:** 5/5
