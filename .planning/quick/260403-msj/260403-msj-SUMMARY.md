---
phase: quick-260403-msj
plan: "01"
type: quick
tags: [scheduler, batch-parse, frontend, backend]
dependency_graph:
  requires: []
  provides:
    - "scheduler_tasks.py: execute_parse_task handles empty novel_name for all-mode"
    - "scheduler_tasks.py: add_parse_job uses 定时解析任务_全部 for empty novel_name"
    - "ScheduledTaskView.vue: 全部解析 option with empty string value"
    - "ScheduledTaskView.vue: dropdown disabled when all-mode selected"
  affects:
    - "ScheduledTaskView.vue: parse form novel dropdown"
    - "scheduler_tasks.py: execute_parse_task and add_parse_job"
tech_stack:
  added: []
  patterns:
    - "Backend conditional query based on empty string sentinel"
    - "Frontend v-if conditional rendering for hint text"
    - "Frontend :disabled binding for select element"
key_files:
  created: []
  modified:
    - "scheduler_tasks.py"
    - "admin/src/views/ScheduledTaskView.vue"
decisions:
  - "Used empty string as sentinel for all-novels mode (not None) to match frontend el-option value="
  - "Kept dropdown but disabled it when all-mode selected (per plan decision)"
  - "Ordered all novels by create_time ascending for consistent processing order"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-03"
---

# Quick Task 260403-msj: 添加全部小说解析功能 Summary

## One-liner

Added "全部解析" (parse all) dropdown option for scheduled batch parse tasks that queries all `current_state=1` novels in creation time order.

## Completed Tasks

| # | Task | Name | Commit | Files |
|---|------|------|--------|-------|
| 1 | Backend: Support all-novels parse mode | `ec2dfe0` | scheduler_tasks.py | Modified execute_parse_task query logic and add_parse_job job naming |
| 2 | Frontend: Add "全部解析" option to dropdown | `ec2dfe0` | admin/src/views/ScheduledTaskView.vue | Added el-option, :disabled binding, hint text span |

## What Was Built

**Backend (scheduler_tasks.py):**
- `execute_parse_task` now checks `if novel_name:` before filtering by novel_name; empty string falls through to query all `current_state=1` novels ordered by `create_time.asc()`
- `add_parse_job` now uses `f"定时解析任务_{novel_name or '全部'}"` so empty novel_name produces job name "定时解析任务_全部"

**Frontend (ScheduledTaskView.vue):**
- Added `<el-option label="全部解析" value="" />` as first entry in the novel dropdown
- Added `:disabled="parseForm.novel_name === ''"` to the el-select
- Added `<span v-if="parseForm.novel_name === ''">已选择全部解析</span>` hint text below the dropdown
- `handleParseNovelChange` already had the else branch that sets `max_chapters = 0` when `novel_name` is falsy

## Verification

| Criterion | Status |
|-----------|--------|
| Backend: execute_parse_task accepts empty novel_name | Verified |
| Backend: add_parse_job uses "定时解析任务_全部" for empty | Verified |
| Frontend: "全部解析" option present | grep found at line 42 |
| Frontend: dropdown disabled when selected | :disabled binding added |
| Frontend: hint text "已选择全部解析" shows | grep found at line 56 |

## Deviations

None - plan executed exactly as written.

## Self-Check: PASSED
