# Milestone v1.0 — Project Summary

**Generated:** 2026-03-31
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**项目名称:** Lively - 有声书生成系统

**核心功能:** 将小说文本自动转换为角色配音的有声书

**目标用户:** 有声书制作团队

**技术栈:**
- 后端: Python 3.12 + FastAPI + Peewee ORM + SQLite
- 前端: Vue 3 + Element Plus + Axios
- AI: Claude API (MiniMax) 文本分析
- 音频: VoxCPM 本地模型生成语音
- 任务调度: APScheduler

**当前状态:** Phase 1 和 Phase 2 已完成

---

## 2. Architecture & Technical Decisions

- **FastAPI REST API** — 提供数据 API 和静态文件服务
- **Vue 3 SPA** — Element Plus UI 组件库
- **SQLite 数据库** — 轻量级，零配置
- **VoxCPM 本地模型** — 保护隐私，离线可用
- **APScheduler** — 异步任务调度
- **WebSocket** — 实时日志推送

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 01 | 统计仪表盘 | ✓ Complete | Vue 3 Dashboard component with 4 stat cards, novel list, and top 50 hot roles table |
| 02 | 批量生成看门狗优化 | ✓ Complete | Watchdog task immediate execution, RTF-only cron check, auto-recovery when RTF>0.8 |

---

## 4. Requirements Coverage

### Phase 1: 统计仪表盘

| Requirement | Status | Notes |
|------------|--------|-------|
| UI-STATS-01: 统计仪表盘页面 | ✅ Complete | 卡片、图表、表格全部实现 |
| UI-STATS-02: 统计 API 端点 | ✅ Complete | 4 个端点全部实现 |

### Phase 2: 批量生成看门狗优化

| Requirement | Status | Notes |
|------------|--------|-------|
| 添加时立即执行 | ✅ Complete | asyncio.create_task() 立即触发 |
| Cron 触发 RTF 检查 | ✅ Complete | 分离 RTF 检查与生成任务 |
| RTF > 0.8 处理 | ✅ Complete | handle_high_rtf() 自动恢复 |

---

## 5. Key Decisions Log

| Decision | Description | Phase |
|----------|-------------|-------|
| D-01 | 卡片网格布局 — el-row/el-col 响应式 | Phase 1 |
| D-05 | Element Plus 内置 charts | Phase 1 |
| D-09~D-12 | 4 个 API 端点分工 | Phase 1 |
| D-13~D-16 | DashboardView.vue 组件结构 | Phase 1 |
| batch_generate_state | 多线程生成状态追踪 | Phase 2 |
| handle_high_rtf | RTF > 0.8 自动恢复 | Phase 2 |

---

## 6. Tech Debt & Deferred Items

**Deferred:**
- 用户权限管理 — 暂时不需要多用户系统
- 音频后期处理（音效、混音）— 不在当前计划
- 多语言支持 — 仅支持中文小说
- 移动端适配 — 后台仅桌面浏览器

**Known Gaps:**
- Phase 1 初始计划使用 el-chart，后因 API 数据格式改为 el-table（已修复）

---

## 7. Getting Started

**运行项目:**
```bash
cd D:/Projects/Python/lively
uvicorn api:app --reload --port 6888
```

**关键目录:**
- `api.py` — FastAPI 主入口，端口 6888
- `scheduler_tasks.py` — 定时任务逻辑
- `bean/beans.py` — 数据库模型
- `generate_audio.py` — 音频生成
- `parse_text.py` — 文本解析
- `admin/src/` — Vue 前端

**前端构建:**
```bash
cd admin
npm install
npm run build
```

---

## Stats

- **Timeline:** 2026-03-30 → 2026-03-31
- **Phases:** 2/2 complete
- **Commits:** 9 (planning)
- **Files Changed:** api.py, scheduler_tasks.py, DashboardView.vue, router, App.vue
