# Plan 02-01: 修改看门狗任务执行逻辑

**Phase:** 02-批量生成看门狗优化
**Wave:** 1
**Autonomous:** yes
**Depends on:** None
**Files Modified:**
- scheduler_tasks.py

---

## Objective

修改看门狗任务逻辑：
1. 添加时立即执行生成（不等待 cron）
2. Cron 触发只检查 RTF
3. RTF > 0.8 时停止 server、等待、重加载模型、恢复任务

---

## Task 1: 添加任务状态追踪变量

<read_first>
- scheduler_tasks.py (line 28-47)
</read_first>

<action>
在 `scheduler_tasks.py` 中添加任务状态追踪变量。

在全局变量区域（约 line 40 附近），`server_instance = None` 之后添加：

```python
# 批量生成任务状态追踪
batch_generate_state = {
    'threads': 0,           # 线程数
    'total_chapters': 0,    # 总章节数
    'completed_chapters': 0, # 已完成章节数
    'is_paused': False,    # 是否暂停
    'is_stopping': False   # 是否正在停止
}
```

并在 `execute_multithread_generate_task` 函数中（约 line 960 附近 `server_instance = None` 之后）找到：
```python
# 记录当前状态
log_info(f"开始执行多线程批量生成任务...")
```

在其后添加状态更新：
```python
# 更新任务状态
batch_generate_state['threads'] = thread_count
batch_generate_state['total_chapters'] = chapter_count
batch_generate_state['completed_chapters'] = 0
batch_generate_state['is_paused'] = False
batch_generate_state['is_stopping'] = False
```
</action>

<acceptance_criteria>
- [ ] `batch_generate_state` 字典已定义
- [ ] 任务开始时初始化状态
</acceptance_criteria>

<verify>
grep -c "batch_generate_state" scheduler_tasks.py
</verify>

<done>
grep -c "batch_generate_state.*threads.*total_chapters.*completed_chapters" scheduler_tasks.py
</done>

---

## Task 2: 修改 add_watchdog_job 函数

<read_first>
- scheduler_tasks.py (line 1541-1572)
</read_first>

<action>
修改 `add_watchdog_job` 函数，使点击添加时立即执行生成任务，而不是等待 cron 触发。

找到 `add_watchdog_job` 函数（约 line 1541），查看其结构：

```python
def add_watchdog_job(job_id: str, cron: str, novel_name: str = '', chapter_count: int = 0, thread_count: int = 0):
    """添加看门狗任务"""
    try:
        # 解析 cron 表达式
        minute, hour, day, month, day_of_week = cron.split()
        ...
        # 添加调度任务
        scheduler.add_job(
            execute_watchdog_task,
            CronTrigger(
                minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
            ),
            args=[job_id, novel_name, chapter_count, thread_count],
            id=job_id,
            replace_existing=True
        )
        ...
```

修改为：在 `scheduler.add_job` 之后，立即调用一次执行：

```python
# 添加调度任务（用于 RTF 检查）
scheduler.add_job(
    execute_watchdog_task,
    CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
    ),
    args=[job_id, novel_name, chapter_count, thread_count],
    id=job_id,
    replace_existing=True
)

# 立即执行一次生成任务（不等待 cron）
log_info(f"🐕 立即开始执行批量生成任务...")
try:
    import asyncio
    asyncio.create_task(execute_watchdog_task(
        job_id=job_id,
        novel_name=novel_name,
        chapter_count=chapter_count,
        thread_count=thread_count,
        log_callback=None
    ))
except Exception as e:
    log_error(f"创建即时任务失败: {e}")
```

注意：如果 `asyncio.create_task` 在非 async 上下文中调用，需要使用 `asyncio.get_event_loop().create_task()` 或直接调用：
```python
# 直接同步调用（execute_watchdog_task 是 async 函数）
loop = asyncio.get_event_loop()
loop.create_task(execute_watchdog_task(...))
```
</action>

<acceptance_criteria>
- [ ] 添加任务时立即执行
- [ ] Cron 触发仍然保留用于 RTF 检查
</acceptance_criteria>

<verify>
grep -c "asyncio.create_task\|create_task" scheduler_tasks.py
</verify>

<done>
grep -c "立即开始执行批量生成任务" scheduler_tasks.py
</done>

---

## Task 3: 修改 execute_watchdog_task 函数

<read_first>
- scheduler_tasks.py (line 1081-1167)
</read_first>

<action>
修改 `execute_watchdog_task` 函数，将生成逻辑和 RTF 检查分离。

当前逻辑（约 line 1120-1137）：
```python
if novel_name and chapter_count > 0:
    log_info(f"🐕 开始执行多线程生成音频任务...")
    ...
    await execute_multithread_generate_task(...)

await check_rtf_in_logs(log_callback)
```

修改为：
1. 生成任务在 cron 触发时不执行（由添加时立即执行）
2. 统一使用 `check_and_handle_rtf()` 函数处理 RTF 检查

将函数重命名为 `rtf_check_task` 或创建新函数 `rtf_check_handler`：

```python
async def rtf_check_handler(job_id: str, log_callback=None):
    """RTF 检查处理函数 - 由 cron 触发"""
    try:
        # 检查 RTF
        is_high_rtf = await check_rtf_in_logs(log_callback)

        if is_high_rtf:
            # RTF > 0.8 处理
            await handle_high_rtf(log_callback)
        else:
            log_info(f"✅ RTF 检查正常")
            if log_callback:
                await log_callback(f"[RTF检查] ✅ RTF 正常，继续监控...\n")

    except Exception as e:
        log_error(f"❌ RTF 检查处理失败: {e}")
```

同时修改 `execute_watchdog_task` 函数，在任务被暂停后恢复执行时检查 RTF。
</action>

<acceptance_criteria>
- [ ] RTF 检查与生成任务分离
- [ ] RTF > 0.8 时有专门处理函数
</acceptance_criteria>

<verify>
grep -c "rtf_check_handler\|handle_high_rtf" scheduler_tasks.py
</verify>

<done>
grep -c "RTF检查正常" scheduler_tasks.py
</done>

---

## Task 4: 添加 handle_high_rtf 函数

<read_first>
- scheduler_tasks.py (line 960-1000) — 查看如何停止和重启 server
</read_first>

<action>
添加 `handle_high_rtf` 函数处理 RTF > 0.8 的情况。

在 `check_rtf_in_logs` 函数之后（约 line 1246）添加：

```python
async def handle_high_rtf(log_callback=None):
    """处理 RTF > 0.8 的情况：停止 server、等待、重加载、恢复任务"""
    global server_instance, batch_generate_state

    try:
        log_warning(f"⚠️"="*60)
        log_warning(f"⚠️ 发现RTF大于0.8，开始处理...")
        log_warning(f"⚠️"="*60)

        if log_callback:
            await log_callback(f"[RTF处理] ⚠️ 发现RTF大于0.8，开始处理...\n")

        # 1. 标记任务为暂停状态
        batch_generate_state['is_paused'] = True
        batch_generate_state['is_stopping'] = True

        # 2. 停止 server
        if server_instance is not None:
            log_info(f"🛑 停止 VoxCPM server...")
            if log_callback:
                await log_callback(f"[RTF处理] 🛑 停止 VoxCPM server...\n")
            await server_instance.stop()
            log_info(f"✅ Server 已停止")
        else:
            log_warning(f"⚠️ server_instance 为 None，跳过停止")

        # 3. 等待 60 秒
        log_info(f"⏳ 等待 60 秒后重新加载模型...")
        if log_callback:
            await log_callback(f"[RTF处理] ⏳ 等待 60 秒...\n")
        await asyncio.sleep(60)

        # 4. 重新加载模型
        log_info(f"🔄 重新加载 VoxCPM 模型...")
        if log_callback:
            await log_callback(f"[RTF处理] 🔄 重新加载模型...\n")

        from nanovllm_voxcpm import VoxCPM

        new_server = VoxCPM.from_pretrained(
            "./VoxCPM1.5/",
            max_num_batched_tokens=8192,
            max_num_seqs=16,
            max_model_len=4096,
            gpu_memory_utilization=0.95,
            enforce_eager=False,
            devices=[0]
        )

        # 5. 更新全局 server 实例
        server_instance = new_server
        set_server_instance(new_server)
        log_info(f"✅ 模型重新加载完成")

        if log_callback:
            await log_callback(f"[RTF处理] ✅ 模型重新加载完成\n")

        # 6. 标记停止完成
        batch_generate_state['is_stopping'] = False

        # 7. 等待 120 秒后恢复任务
        log_info(f"⏳ 等待 120 秒后恢复任务...")
        if log_callback:
            await log_callback(f"[RTF处理] ⏳ 等待 120 秒后恢复任务...\n")
        await asyncio.sleep(120)

        # 8. 恢复任务
        if batch_generate_state['is_paused']:
            batch_generate_state['is_paused'] = False
            log_info(f"🔄 恢复批量生成任务...")
            if log_callback:
                await log_callback(f"[RTF处理] 🔄 恢复批量生成任务...\n")
            # 触发恢复执行
            # 注意：这里需要根据实际的任务队列机制来决定如何恢复

    except Exception as e:
        log_error(f"❌ 处理 RTF 失败: {e}")
        if log_callback:
            await log_callback(f"[RTF处理] ❌ 处理失败: {e}\n")
        batch_generate_state['is_stopping'] = False
```

注意：恢复任务的机制需要根据实际批量生成任务的实现来决定。如果使用线程池，需要能够恢复线程池中的任务。
</action>

<acceptance_criteria>
- [ ] `handle_high_rtf` 函数已添加
- [ ] 包含停止 server、等待、重加载、恢复的完整逻辑
</acceptance_criteria>

<verify>
grep -c "handle_high_rtf" scheduler_tasks.py
</verify>

<done>
grep -c "server_instance.stop\|重新加载" scheduler_tasks.py
</done>

---

## Task 5: 修改多线程生成任务以支持状态追踪

<read_first>
- scheduler_tasks.py (line 560-700)
</read_first>

<action>
修改 `execute_single_chapter_from_queue` 函数，在每个章节完成时更新 `batch_generate_state['completed_chapters']`。

在章节生成成功后（约 line 700 附近），找到成功完成的日志后，添加：

```python
# 更新已完成章节计数
if 'completed_chapters' in batch_generate_state:
    batch_generate_state['completed_chapters'] += 1
    remaining = batch_generate_state['total_chapters'] - batch_generate_state['completed_chapters']
    log_info(f"📊 任务进度: {batch_generate_state['completed_chapters']}/{batch_generate_state['total_chapters']} 完成，剩余 {remaining}")
    if log_callback:
        await log_callback(f"[进度] {batch_generate_state['completed_chapters']}/{batch_generate_state['total_chapters']} 完成，剩余 {remaining}\n")
```

同时在 `execute_multithread_generate_task` 函数中，如果检测到 `is_paused` 或 `is_stopping` 为 True，需要等待：

在任务开始执行线程池之前（约 line 850 附近），添加：

```python
# 检查是否需要暂停
if batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
    log_info(f"⏸️ 任务已暂停，等待恢复...")
    if log_callback:
        await log_callback(f"[任务] ⏸️ 任务已暂停，等待恢复...\n")

    # 等待暂停标志清除
    while batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
        await asyncio.sleep(5)

    log_info(f"▶️ 任务恢复执行")
    if log_callback:
        await log_callback(f"[任务] ▶️ 任务恢复执行\n")
```

</action>

<acceptance_criteria>
- [ ] 完成章节时更新计数
- [ ] 任务开始时检查暂停状态
</acceptance_criteria>

<verify>
grep -c "completed_chapters.*+=" scheduler_tasks.py
</verify>

<done>
grep -c "is_paused.*is_stopping" scheduler_tasks.py
</done>

---

## Verification Criteria

1. 添加看门狗任务时立即开始执行
2. Cron 触发时执行 RTF 检查
3. RTF > 0.8 时执行停止、重加载、恢复流程
4. 任务状态正确追踪

## must_haves

- [x] `batch_generate_state` 变量追踪任务进度
- [x] 点击添加立即执行生成
- [x] RTF > 0.8 时停止并重加载模型
- [x] 任务恢复后继续执行剩余章节
