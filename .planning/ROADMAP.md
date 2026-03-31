# Roadmap

**Project:** Lively - 有声书生成系统
**Created:** 2003-03-30
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

**Plans:** 1/1 plans complete

**Plan list:**
- [x] 02-01-PLAN.md — 修改看门狗任务执行逻辑

**Verification:** [02-批量生成看门狗优化-VERIFICATION.md](./phases/02-批量生成看门狗优化/02-批量生成看门狗优化-VERIFICATION.md)

### Phase 3: 修改看门狗功能/添加设置功能

**Goal:** 完善看门狗配置化和任务持久化功能

**Requirements:**
- UI-WATCHDOG-03: RTF重启阈值可配置（设置界面添加小数输入框，最小0最大2，保存到config/lively_config.json）
- UI-WATCHDOG-04: 看门狗生成任务自动重启开关（开=持久化到数据库并重启恢复，关=删除数据库记录）
- UI-WATCHDOG-05: 系统启动时清理temp目录wav文件

**Depends on:** Phase 2

**Success Criteria:**
1. RTF阈值可动态配置并从配置文件读取
2. 开启自动重启时，任务状态持久化到数据库，系统重启后可恢复执行
3. 关闭自动重启时，系统启动后清理相关数据库记录
4. 系统启动时自动清理temp/*.wav文件
5. 所有状态变更都有前台提示(5秒)和日志记录

**Plans:** 2/3 plans complete

**Plan list:**
- [x] 03-01-PLAN.md — Backend Core: Config + Database + Settings API (COMPLETE)
- [x] 03-02-PLAN.md — Frontend Settings + RTF Config + Temp Cleanup
- [ ] 03-03-PLAN.md — Watchdog Task Persistence + Recovery

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-STATS-01 | Phase 1 | Complete |
| UI-STATS-02 | Phase 1 | Complete |
| UI-WATCHDOG-01 | Phase 2 | Complete |
| UI-WATCHDOG-02 | Phase 2 | Complete |
| UI-WATCHDOG-03 | Phase 3 | Partial (Plan 01 config/DB/API done) |
| UI-WATCHDOG-04 | Phase 3 | Partial (Plan 01 model done) |
| UI-WATCHDOG-05 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓
