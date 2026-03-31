# Requirements

## v1 Requirements

### UI-STATS-01: 统计仪表盘页面

**描述:** 创建综合统计仪表盘页面，作为管理后台的首页或独立菜单项

**内容要求:**
- [ ] 小说统计卡片：显示小说总数
- [ ] 章节统计：显示所有小说的总章节数、平均每本章节数
- [ ] 角色统计：显示角色总数、每本小说的角色数
- [ ] 热门角色列表：显示前 50 个热门角色（按引用次数排序）
- [ ] 音频统计卡片：显示已生成音频数量
- [ ] 未生成章节：显示有多少章节还未生成音频
- [ ] 未解析小说：显示有多少小说还未进行 AI 解析
- [ ] 图表混合展示：数字卡片 + 简单图表（柱状图/饼图）

**验收标准:**
- 页面加载时间 < 2 秒
- 数据从 API 获取并实时显示
- 响应式布局，适配不同屏幕

### UI-STATS-02: 统计 API 端点

**描述:** 创建后端 API 端点为仪表盘提供数据

**端点要求:**
- [x] `GET /api/stats/overview` — 返回全局统计概览
  - 小说总数、章节总数、角色总数、音频总数
- [x] `GET /api/stats/novels` — 返回小说统计
  - 每本小说的章节数、角色数、解析状态、生成状态
- [x] `GET /api/stats/roles/top` — 返回热门角色
  - 前 50 个角色，按引用次数排序
- [x] `GET /api/stats/pending` — 返回待处理统计
  - 未解析小说数、未生成章节数

**验收标准:**
- API 响应格式统一
- 支持分页（如需要）
- 错误处理完善

### UI-WATCHDOG-03: RTF重启阈值可配置

**描述:** 在设置界面添加 RTF 重启阈值配置项

**配置要求:**
- [x] RTF 阈值输入框（el-input-number）
  - 最小值 0，最大值 2，step 0.1，精度 2 位小数
- [x] 保存到 config/lively_config.json 的 rtf_threshold 字段
- [x] scheduler_tasks.py 从配置文件读取，而非硬编码 0.8
- [x] 日志和打印信息动态显示实际使用的 RTF 值

**验收标准:**
- 配置值保存后重启任务仍生效
- 日志中显示的 RTF 值与配置一致

### UI-WATCHDOG-04: 看门狗生成任务自动重启开关

**描述:** 添加看门狗任务持久化和自动恢复功能

**开关要求:**
- [x] 设置界面添加"看门狗生成任务自动重启"开关（el-switch）
- [x] 默认开启（watchdog_auto_recovery: true）
- [x] 开关状态保存到 config/lively_config.json

**持久化要求:**
- [x] 创建 watchdog_tasks 数据库表
- [x] 任务执行时记录 job_id, novel_name, thread_count, total_chapters, completed_chapters, is_running
- [x] 每完成一章更新 completed_chapters
- [x] 系统启动时恢复未完成的任务（WebSocket 推送消息）

**开关关闭行为:**
- [x] 系统启动后删除 watchdog_tasks 表中所有记录
- [x] 显示 5 秒提示，控制台和日志同时记录

### UI-WATCHDOG-05: 系统启动时清理temp目录wav文件

**描述:** 系统启动时自动清理临时音频文件

**清理要求:**
- [x] 系统启动时调用 cleanup_temp_wavs() 函数
- [x] 删除 temp/*.wav 文件
- [x] 不提供手动清理按钮或 API

**验收标准:**
- temp 目录下无残留 wav 文件
- 清理后系统正常运行

## v2 Requirements (Deferred)

- 用户管理功能（多用户、权限控制）
- 批量操作功能（批量解析、批量生成）
- 导出功能（导出统计数据到 Excel）

## Out of Scope

- 用户权限管理系统 — 暂时不需要
- 音频后期处理（音效、混音）— 不在当前计划
- 多语言支持 — 仅中文
- 移动端适配 — 后台仅桌面浏览器

---

*Traceability: UI-STATS-01, UI-STATS-02 → Phase 1; UI-WATCHDOG-03, UI-WATCHDOG-04, UI-WATCHDOG-05 → Phase 3*
