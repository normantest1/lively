# Plan 01-GAP-01: Fix Phase 1 Verification Gaps

**Phase:** 01-统计仪表盘
**Wave:** 1
**Type:** Gap Closure
**Autonomous:** yes
**Depends on:** None
**Files Modified:**
- api.py
- admin/src/views/DashboardView.vue

---

## Objective

修复 Phase 1 验证发现的两个问题：
1. 添加平均每本章节数到 overview API
2. 用 el-chart 替代 el-table 显示小说状态分布

---

## Task 1: Add avg_chapters_per_novel to overview API

<read_first>
- api.py (line ~1301-1320)
</read_first>

<action>
在 `/api/stats/overview` 端点中添加 `avg_chapters_per_novel` 字段。

修改 api.py 第 1315-1320 行，将 return 语句从：
```python
return {
    "total_novels": total_novels,
    "total_chapters": total_chapters,
    "total_roles": total_roles,
    "total_audios": total_audios
}
```

修改为：
```python
avg_chapters = total_chapters / total_novels if total_novels > 0 else 0
return {
    "total_novels": total_novels,
    "total_chapters": total_chapters,
    "avg_chapters_per_novel": round(avg_chapters, 2),
    "total_roles": total_roles,
    "total_audios": total_audios
}
```
</action>

<acceptance_criteria>
- [ ] api.py 包含 `avg_chapters_per_novel` 字段
- [ ] 该字段计算为 total_chapters / total_novels，保留两位小数
- [ ] 当 total_novels 为 0 时返回 0
</acceptance_criteria>

<verify>
grep "avg_chapters_per_novel" api.py
</verify>

<done>
grep -c "avg_chapters_per_novel.*total_chapters.*total_novels" api.py
</done>

---

## Task 2: Add avg_chapters to chapter stats display

<read_first>
- admin/src/views/DashboardView.vue (line ~59-77)
</read_first>

<action>
在 DashboardView.vue 的章节统计 Summary 部分（第 59-77 行），在显示"总章节数"后添加"平均每本章节数"。

在第 67 行后添加：
```html
</el-col>
<el-col :span="12">
  <div class="info-card">
    <div class="info-item">
      <span class="info-label">平均每本章节数：</span>
      <span class="info-value">{{ overview.avg_chapters_per_novel || 0 }}</span>
    </div>
  </div>
</el-col>
```
</action>

<acceptance_criteria>
- [ ] DashboardView.vue 显示 avg_chapters_per_novel
- [ ] 使用与 total_chapters 相同的样式
</acceptance_criteria>

<verify>
grep "avg_chapters_per_novel" admin/src/views/DashboardView.vue
</verify>

<done>
grep -c "平均每本章节数" admin/src/views/DashboardView.vue
</done>

---

## Task 3: Replace el-table with el-chart for novel state distribution

<read_first>
- admin/src/views/DashboardView.vue (line ~80-120)
- Element Plus el-chart documentation
</read_first>

<action>
将小说状态分布从 el-table 改为 el-chart (柱状图)。

1. 首先在 script setup 部分添加计算属性：
```javascript
// 计算小说状态分布数据
const stateDistribution = computed(() => {
  const stats = { 1: 0, 2: 0, 3: 0 }
  novels.value.forEach(novel => {
    if (novel.current_state in stats) {
      stats[novel.current_state]++
    }
  })
  return [
    { state: '已分片待解析', count: stats[1] },
    { state: '已解析待合成', count: stats[2] },
    { state: '已合成语音', count: stats[3] }
  ]
})
```

2. 然后将模板中的 el-table 区域（第 81-105 行）替换为：
```html
<el-card class="chart-card">
  <template #header>
    <div class="card-header">
      <span>小说状态分布</span>
    </div>
  </template>
  <div class="chart-container" v-loading="loading">
    <el-chart :option="stateChartOption" autoresize style="height: 300px" />
  </div>
</el-card>
```

3. 在 script 中添加：
```javascript
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const stateChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: stateDistribution.value.map(d => d.state)
  },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    data: stateDistribution.value.map(d => d.count),
    itemStyle: {
      color: (params) => ['#409eff', '#e6a23c', '#67c23a'][params.dataIndex]
    }
  }]
}))
```

注意：如果 Element Plus 的 el-chart 不能直接使用 echarts，需要安装：
```bash
cd admin && npm install echarts vue-echarts
```
如果已有 echarts，直接使用上述代码。
</action>

<acceptance_criteria>
- [ ] DashboardView.vue 使用 el-chart 显示小说状态分布
- [ ] 图表显示三个状态的数量：已分片待解析、已解析待合成、已合成语音
- [ ] 如果需要安装 echarts，也安装到 package.json
</acceptance_criteria>

<verify>
grep -c "el-chart\|vue-echarts\|echarts" admin/src/views/DashboardView.vue
</verify>

<done>
grep -c "stateChartOption\|stateDistribution" admin/src/views/DashboardView.vue
</done>

---

## Verification Criteria

1. GET /api/stats/overview 返回 avg_chapters_per_novel 字段
2. Dashboard 显示平均每本章节数
3. Dashboard 使用图表（而非表格）显示小说状态分布

## must_haves

- [x] API 返回 avg_chapters_per_novel
- [x] Dashboard 显示该字段
- [x] 小说状态使用图表展示
