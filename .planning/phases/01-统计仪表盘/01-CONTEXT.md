# Phase 1: 统计仪表盘 - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

创建综合统计仪表盘页面，展示小说、角色、音频数据概览。后台 API 提供数据，前端 Vue 组件展示。

</domain>

<decisions>
## Implementation Decisions

### Layout
- **D-01:** 卡片网格布局 — 使用 `<el-row>` 和 `<el-col>` 构建响应式网格
- **D-02:** 顶部统计卡片区 — 4 个数字卡片（小说总数、角色总数、音频总数、待处理）
- **D-03:** 中部图表区 — 柱状图/饼图展示分布数据
- **D-04:** 底部详细列表 — 表格展示具体数据

### Chart Library
- **D-05:** Element Plus 内置 charts — 使用 Element Plus 2.5+ 的 el-chart 组件
- **D-06:** 暂不引入外部图表库 — 保持依赖精简

### Data Refresh
- **D-07:** 手动刷新 — 用户点击刷新按钮更新数据
- **D-08:** 页面加载时自动请求一次数据

### API Endpoints
- **D-09:** `/api/stats/overview` — 全局概览（小说总数、角色总数、音频总数、待处理数）
- **D-10:** `/api/stats/novels` — 小说列表及章节/角色统计
- **D-11:** `/api/stats/roles/top?limit=50` — 前50热门角色
- **D-12:** `/api/stats/pending` — 待处理统计（未解析小说数、未生成章节数）

### Vue Component
- **D-13:** 组件命名：`DashboardView.vue`
- **D-14:** 位置：`admin/src/views/DashboardView.vue`
- **D-15:** 路由：`/dashboard` 或 `/` (首页)
- **D-16:** 组合式 API — 使用 `<script setup>` 语法

### Data Card Metrics
- **D-17:** 小说总数 — 从 overview 端点获取
- **D-18:** 角色总数 — 从 overview 端点获取
- **D-19:** 音频总数 — 从 overview 端点获取
- **D-20:** 待处理数 — 从 pending 端点获取（未解析 + 未生成）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `admin/src/views/NovelManage.vue` — Vue 组件模式参考
- `admin/src/api/index.js` — API 调用模式
- `api.py` 第 1262-1279 行 — 已有 `/api/statistics/*` 端点参考

### Templates
- Element Plus Card 组件文档
- Element Plus Chart 组件文档

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin/src/api/index.js` — API 请求函数，可复用 `request()` 模式
- Element Plus `<el-card>` — 统计卡片布局
- Element Plus `<el-table>` — 数据列表展示
- Element Plus `<el-row>/<el-col>` — 响应式网格

### Established Patterns
- Vue 3 Composition API (`<script setup>`)
- Axios 请求 → Promise → async/await
- Element Plus 组件按需引入

### Integration Points
- API: 在 `api.py` 中新增 `/api/stats/*` 路由
- 前端路由: 在 `admin/src/router/` 中添加路由
- 菜单: 在 Element Plus menu 中添加入口

</code_context>

<specifics>
## Specific Ideas

**卡片布局：**
```
┌─────────┬─────────┬─────────┬─────────┐
│ 小说总数 │ 角色总数 │ 音频总数 │ 待处理  │
└─────────┴─────────┴─────────┴─────────┘
┌─────────────────┬─────────────────────┐
│                 │                     │
│   小说分布图     │    角色分布饼图      │
│                 │                     │
└─────────────────┴─────────────────────┘
┌─────────────────────────────────────────┐
│         前 50 热门角色列表               │
│  (表格：角色名 | 所属小说 | 引用次数)     │
└─────────────────────────────────────────┘
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-统计仪表盘*
*Context gathered: 2026-03-30*
