# Phase 02 Plan 02: 批量生成看门狗优化 - Verification

**Plan:** 02-批量生成看门狗优化
**Verification Date:** 2026-03-31
**Status:** PASSED

## Must-Haves Verification

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | `batch_generate_state` variable tracks task progress | PASS | Lines 44-51, 828-832: defined with keys `threads`, `total_chapters`, `completed_chapters`, `is_paused`, `is_stopping` |
| 2 | Click add triggers immediate generation | PASS | Lines 1683-1695: `add_watchdog_job` calls `loop.create_task(execute_watchdog_task(...))` with actual `novel_name`, `chapter_count`, `thread_count` |
| 3 | RTF > 0.8 triggers server stop and model reload | PASS | Lines 1294-1371: `handle_high_rtf` function implements full stop/wait60s/reload/wait120s/resume flow; Lines 1178-1179: called when `is_high_rtf` is True |
| 4 | Task resumes and continues remaining chapters | PASS | Lines 1026-1075: After reload, queries remaining `current_state=2` chapters, rebuilds queue, creates new workers with `task_cancel_event` |

## Code Spot-Checks

### batch_generate_state Definition
```python
# Line 44-51
batch_generate_state = {
    'threads': 0,           # 线程数
    'total_chapters': 0,    # 总章节数
    'completed_chapters': 0, # 已完成章节数
    'is_paused': False,      # 是否暂停
    'is_stopping': False     # 是否正在停止
}
```

### Immediate Execution on Add
```python
# Lines 1683-1695
log_info(f"🐕 立即开始执行批量生成任务...")
try:
    loop = asyncio.get_event_loop()
    loop.create_task(execute_watchdog_task(
        job_id=job_id,
        novel_name=novel_name,
        chapter_count=chapter_count,
        thread_count=thread_count,
        log_callback=None
    ))
```

### RTF > 0.8 Recovery Logic
```python
# Lines 1294-1371
async def handle_high_rtf(log_callback=None):
    """处理 RTF > 0.8 的情况：停止 server、等待、重加载、恢复任务"""
    # 1. Mark paused/stopping
    # 2. Stop server
    # 3. Wait 60 seconds
    # 4. Reload model
    # 5. Wait 120 seconds
    # 6. Resume task
```

### Task Progress Tracking
```python
# Lines 688-693
if 'completed_chapters' in batch_generate_state:
    batch_generate_state['completed_chapters'] += 1
    remaining = batch_generate_state['total_chapters'] - batch_generate_state['completed_chapters']
    log_info(f"📊 任务进度: {batch_generate_state['completed_chapters']}/{batch_generate_state['total_chapters']} 完成，剩余 {remaining}")
```

### Pause/Resume Check
```python
# Lines 912-923
if batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
    log_info(f"⏸️ 任务已暂停，等待恢复...")
    while batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
        await asyncio.sleep(5)
    log_info(f"▶️ 任务恢复执行")
```

## Commits Verification

| Commit | Description | Verified |
|--------|-------------|----------|
| e32ad3a | Add batch_generate_state tracking variable | Yes |
| fd4622a | Execute watchdog task immediately on add | Yes |
| 4ed08a7 | Separate RTF check from generation | Yes |
| a23e815 | Add handle_high_rtf function for RTF>0.8 recovery | Yes |
| fa8e747 | Add state tracking to multi-thread generate | Yes |
| 8bf818c | Complete plan with SUMMARY.md, update STATE.md | Yes |

## Summary

All 4 must-haves verified present in code. The plan was executed correctly with 5 tasks and 6 commits. No deviations found.

**Result:** VERIFIED PASSED
