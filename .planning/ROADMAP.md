# Roadmap

**Project:** Lively - 有声书生成系统
**Created:** 2026-03-30
**Core Value:** 将小说文本自动转换为角色配音的有声书

## Phase 1: 统计仪表盘

**Goal:** 创建综合统计仪表盘，展示小说、角色、音频数据

**Requirements:**
- UI-STATS-01: 统计仪表盘页面
- UI-STATS-02: 统计 API 端点

**Success Criteria:**
1. 仪表盘页面能正常加载，显示所有统计卡片
2. API 端点返回正确的数据格式
3. 前 50 热门角色列表正确显示
4. 未解析/未生成数据准确统计
5. 页面响应式布局正常

**Plans:** 3/3 plans complete

**Plan list:**
- [x] 01-01-PLAN.md — Backend API: overview + pending endpoints
- [x] 01-02-PLAN.md — Backend API: novels + top roles endpoints
- [x] 01-03-PLAN.md — Frontend: DashboardView component

**UI hint:** yes

---

## Phase 2: 批量生成看门狗优化

**Goal:** 优化定时任务逻辑，添加时立即生成音频，cron 表达式用于触发 RTF 检查

**Requirements:**
- UI-WATCHDOG-01: 修改看门狗任务添加逻辑（点击添加立即生成）
- UI-WATCHDOG-02: 修改 cron 触发逻辑（仅检查 RTF > 0.8）

**Success Criteria:**
1. 点击添加后后台立即开始生成音频任务
2. Cron 表达式触发 RTF 检查（最新 log 文件最后 10 行，RTF > 0.8）
3. 原有多线程生成逻辑保持不变

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-STATS-01 | Phase 1 | Complete |
| UI-STATS-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 2 total
- Mapped to phases: 2
- Unmapped: 0 ✓

---

*Last updated: 2026-03-30 after Phase 1 Plan 03 complete*
