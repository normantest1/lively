# Phase 2: 批量生成看门狗优化 - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

修改批量生成看门狗任务的执行逻辑：
1. 点击"添加"按钮时立即开始生成音频任务
2. Cron 表达式仅用于触发 RTF 检查（不是触发生成）
3. RTF > 0.8 时停止 server、等待、重加载模型、恢复任务

</domain>

<decisions>
## Implementation Decisions

### Task 1: 修改添加逻辑
- **D-01:** 点击"添加"时立即调用执行函数（`execute_watchdog_task`）
- **D-02:** Cron 表达式作为参数存储，但不在添加时触发

### Task 2: 修改 Cron 触发逻辑
- **D-03:** Cron 触发只执行 `check_rtf_in_logs()`
- **D-04:** 检查最新 log 文件最后 10 行的 RTF 值

### Task 3: RTF > 0.8 处理
- **D-05:** 打印警告到控制台
- **D-06:** 记录警告到日志
- **D-07:** 调用 `await server.stop()` 停止 server
- **D-08:** 等待 60 秒
- **D-09:** 重新加载 VoxCPM 模型
- **D-10:** 赋值到全局变量 `server`

### Task 4: 任务状态记录与恢复
- **D-11:** 使用全局变量记录任务状态：
  - `watchdog_task_threads`: 线程数
  - `watchdog_task_total_chapters`: 总章节数
  - `watchdog_task_completed_chapters`: 已完成章节数
- **D-12:** 停止后等待 120 秒
- **D-13:** 恢复任务时使用记录的参数重新执行

### API Server 访问
- **D-14:** `api.py` 中的 `server` 是全局变量
- **D-15:** `scheduler_tasks.py` 需要通过 `server_instance` 访问或导入

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `scheduler_tasks.py` line 1081-1167 — `execute_watchdog_task` 函数
- `scheduler_tasks.py` line 1169-1246 — `check_rtf_in_logs` 函数
- `scheduler_tasks.py` line 1492-1572 — `add_watchdog_job` 函数
- `scheduler_tasks.py` line 44-47 — 全局锁定义
- `scheduler_tasks.py` line 28-39 — 运行状态标志
- `api.py` line 185-200 — VoxCPM server 定义和初始化
- `api.py` line 188 — `await server.stop()` 调用

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `check_rtf_in_logs()` — 已有 RTF 检查逻辑，直接复用
- `execute_multithread_generate_task()` — 已有批量生成逻辑
- 全局锁机制 — 防止并发问题

### Integration Points
- `api.py` 的 `server` 全局变量 — 需要导入或通过函数访问
- `scheduler_tasks.py` 的 `execute_watchdog_task` — 需要重构

### Key Variables to Track
```python
watchdog_task_threads = 0      # 线程数
watchdog_task_total_chapters = 0  # 总章节数
watchdog_task_completed_chapters = 0  # 已完成章节数
```

</code_context>

<specifics>
## Specific Ideas

**新增变量：**
```python
# 任务状态追踪
watchdog_task_state = {
    'threads': 0,
    'total_chapters': 0,
    'completed_chapters': 0,
    'is_paused': False
}
```

**RTF > 0.8 处理流程：**
```
1. log_callback("⚠️ 发现RTF大于0.8: {rtf_value}")
2. 打印警告到控制台
3. await server.stop()
4. 等待 60 秒
5. 重新加载模型
6. 更新 watchdog_task_state['is_paused'] = False
7. 恢复执行
```

**恢复执行：**
```
1. 从 watchdog_task_state 读取参数
2. 检查 is_paused 状态
3. 如果是暂停状态，等待 120 秒
4. 重置 is_paused = False
5. 继续执行剩余章节
```

</specifics>

<deferred>
## Deferred Ideas

None — requirements fully specified

</deferred>

---

*Phase: 02-批量生成看门狗优化*
*Context gathered: 2026-03-31*
