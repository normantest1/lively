# Phase 3: 修改看门狗功能/添加设置功能 - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

完善看门狗配置化和任务持久化功能：
1. RTF 重启阈值可配置（0-2 小数，设置界面输入，保存到 config/lively_config.json）
2. 看门狗生成任务自动重启开关（开=持久化到数据库并重启恢复，关=删除数据库记录）
3. 系统启动时清理 temp/*.wav 文件

</domain>

<decisions>
## Implementation Decisions

### RTF 阈值配置
- **D-01:** RTF 阈值使用 el-input-number 输入框，最小值 0，最大值 2，step 0.1，精度 2 位小数
- **D-02:** RTF 阈值保存到 config/lively_config.json 的 `rtf_threshold` 字段
- **D-03:** 相关日志和打印信息需要动态显示实际使用的 RTF 值（而非硬编码 0.8）

### 看门狗任务持久化
- **D-04:** 创建新的 `watchdog_tasks` 数据库表（独立于 ScheduledTask）
- **D-05:** watchdog_tasks 表字段：id, job_id, novel_name, thread_count, total_chapters, completed_chapters, is_running, create_time, update_time
- **D-06:** 开关默认状态为**开启**（auto_recovery_enabled: true）
- **D-07:** 开关状态保存在 config/lively_config.json 的 `watchdog_auto_recovery` 字段

### 启动恢复行为
- **D-08:** 系统启动时，通过 WebSocket 实时推送恢复消息到前端
- **D-09:** 恢复时显示 5 秒提示，包含任务信息（小说名、线程数、总章节、已完成章节）
- **D-10:** 同时输出到控制台和日志文件

### 关闭开关行为
- **D-11:** 关闭开关时，系统启动后删除 watchdog_tasks 表中所有记录
- **D-12:** 显示 5 秒提示，控制台和日志同时记录

### Temp 清理
- **D-13:** 仅在系统启动时自动清理 temp/*.wav 文件
- **D-14:** 不提供手动清理按钮或 API

### 前期决策（继承）
- **D-15:** RTF 检查使用日志最后 10 行（来自 Phase 2）
- **D-16:** batch_generate_state 全局字典用于内存中的任务跟踪（来自 Phase 2）
- **D-17:** 60 秒 reload wait、120 秒 resume wait（来自 Phase 2 的硬编码值将通过配置化解决）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `scheduler_tasks.py` line 1269 — RTF 检查 `if rtf_value > 0.8:` （需替换为配置读取）
- `scheduler_tasks.py` line 45-51 — `batch_generate_state` 全局变量
- `scheduler_tasks.py` line 1295-1373 — `handle_high_rtf()` 函数
- `scheduler_tasks.py` line 1216-1288 — `check_rtf_in_logs()` 函数
- `api.py` line 1786-1825 — SettingsRequest 模型和 GET/POST /api/settings
- `admin/src/views/SettingsView.vue` — 设置页面 Vue 组件
- `bean/beans.py` line 74-88 — ScheduledTask 模型

### Config File
- `config/lively_config.json` — 设置持久化文件

### Phase Context
- `.planning/phases/02-批量生成看门狗优化/02-CONTEXT.md` — Phase 2 上下文

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- SettingsRequest Pydantic model — 已有设置模型，可直接扩展
- SettingsView.vue el-divider 分区模式 — 可复用分区样式添加看门狗设置
- WebSocket 推送模式 — 参考现有的日志推送实现
- batch_generate_state — 内存状态追踪模式

### Established Patterns
- 配置读取使用 `load_config()` 函数
- 日志使用 `log_info()`, `log_warning()`, `log_error()` 函数
- 前端提示使用 `ElMessage` 组件

### Integration Points
- 数据库：新增 watchdog_tasks 表
- API：settings GET/POST 端点
- WebSocket：日志推送通道复用
- Config：lively_config.json

</code_context>

<specifics>
## Specific Ideas

**watchdog_tasks 表结构：**
```python
class WatchdogTask(BaseModel):
    id = AutoField(primary_key=True)
    job_id = CharField(max_length=100, unique=True)
    novel_name = CharField(max_length=100)
    thread_count = IntegerField(default=4)
    total_chapters = IntegerField()
    completed_chapters = IntegerField(default=0)
    is_running = BooleanField(default=False)
    create_time = DateTimeField(default=datetime.datetime.now)
    update_time = DateTimeField(default=datetime.datetime.now)
```

**config/lively_config.json 新增字段：**
```json
{
  "rtf_threshold": 0.8,
  "watchdog_auto_recovery": true,
  "watchdog_reload_wait_seconds": 60,
  "watchdog_resume_wait_seconds": 120,
  "watchdog_log_check_lines": 10
}
```

**SettingsView.vue 新增配置分区：**
```
┌─────────────────────────────────────┐
│ RTF 重启阈值                         │
│ [0.1 ────●──── 2] (输入框)          │
├─────────────────────────────────────┤
│ 看门狗生成任务自动重启                 │
│ [开关 ●——]                         │
└─────────────────────────────────────┘
```

**WebSocket 恢复消息格式：**
```json
{
  "type": "watchdog_recovery",
  "message": "恢复看门狗任务: {novel_name}, 线程: {thread_count}, 进度: {completed}/{total}",
  "duration": 5
}
```

</specifics>

<deferred>
## Deferred Ideas

None — all requirements discussed and captured

</deferred>

---

*Phase: 03-修改看门狗功能-添加设置功能*
*Context gathered: 2026-03-31*
