# Lively - 有声书生成系统

## What This Is

一个有声书生成系统，用户上传小说文本，系统通过 AI 分析提取角色对话，将角色绑定音频后使用 VoxCPM 模型生成语音片段，最终合成为完整有声书。

## Core Value

将小说文本自动转换为角色配音的有声书

## Requirements

### Validated

- ✓ 小说上传与分章 — 用户上传 TXT 文件，系统按章节分割
- ✓ AI 角色解析 — 使用 Claude/MiniMax API 分析文本提取角色和对话
- ✓ 角色音频绑定 — 用户为角色绑定音频样本
- ✓ VoxCPM 语音生成 — 本地 VoxCPM 模型生成角色语音
- ✓ Vue.js 后台管理 — Element Plus UI 管理小说、角色、音频
- ✓ 定时任务调度 — APScheduler 管理解析和生成任务

### Active

- [ ] **统计仪表盘** — 小说/角色/音频的综合统计页面
  - 小说统计：数量、每本章节数
  - 角色统计：每本角色数、前50热门角色
  - 音频统计：已生成数量、未生成章节、未解析小说
  - 风格：数字卡片 + 图表混合

### Out of Scope

- 用户权限管理 — 暂时不需要多用户系统
- 音频后期处理 — 不添加音效、混音功能
- 多语言支持 — 仅支持中文小说
- 移动端适配 — 后台管理仅考虑桌面浏览器

## Context

**现有系统架构：**
- 后端：FastAPI + Peewee ORM + SQLite
- 前端：Vue 3 + Vue Router + Element Plus + Axios
- AI：Claude API (MiniMax) 用于文本分析
- 音频：VoxCPM 本地模型生成语音

**数据模型：**
- Novel：小说（状态：1=已分片待解析, 2=已解析待合成, 3=已合成语音）
- Role：角色（is_bind 标识是否绑定音频）
- RoleAudio：角色音频样本
- ScheduledTask：定时任务

**API 端点：**
- `/api/novels/*` — 小说管理
- `/api/roles/*` — 角色管理
- `/api/role-audios/*` — 音频管理
- `/api/tasks/*` — 任务管理
- `/api/stats/*` — 统计相关（需新增）

## Constraints

- **技术栈锁定**: Python 3.12 + FastAPI + Vue 3 — 不得更换
- **数据库**: SQLite — 暂不迁移到其他数据库
- **GPU 要求**: VoxCPM 需要 CUDA GPU — 部署环境必须满足
- **API 依赖**: 需要 MiniMax API Key — 必须配置

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vue 3 + Element Plus | 团队熟悉 Vue，Element Plus 组件丰富 | ✓ Good |
| SQLite 数据库 | 轻量级，零配置，适合单机部署 | ✓ Good |
| VoxCPM 本地模型 | 保护隐私，离线可用 | ✓ Good |
| 统计页面混合风格 | 重要指标用卡片，趋势用图表 | — Pending |
| 前50热门角色 | 限制展示数量保证性能 | — Pending |

---

*Last updated: 2026-03-30 after initialization*
