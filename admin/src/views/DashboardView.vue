<template>
  <div class="dashboard">
    <el-card class="refresh-card">
      <template #header>
        <div class="card-header">
          <span>统计概览</span>
          <el-button type="primary" @click="loadData" :loading="loading">刷新数据</el-button>
        </div>
      </template>

      <!-- 4 Stat Cards -->
      <el-row :gutter="20" class="stat-row">
        <el-col :span="6">
          <div class="stat-card stat-novels">
            <div class="stat-icon">
              <el-icon :size="40"><Reading /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ overview.total_novels || 0 }}</div>
              <div class="stat-label">小说总数</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-roles">
            <div class="stat-icon">
              <el-icon :size="40"><User /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ overview.total_roles || 0 }}</div>
              <div class="stat-label">角色总数</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-audios">
            <div class="stat-icon">
              <el-icon :size="40"><Microphone /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ overview.total_audios || 0 }}</div>
              <div class="stat-label">音频总数</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-pending">
            <div class="stat-icon">
              <el-icon :size="40"><Warning /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ (pending.unparsed_novels || 0) + (pending.ungenerated_chapters || 0) }}</div>
              <div class="stat-label">待处理</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Chapter Stats Summary -->
      <el-row :gutter="20" class="stat-row">
        <el-col :span="8">
          <div class="info-card">
            <div class="info-item">
              <span class="info-label">总章节数：</span>
              <span class="info-value">{{ overview.total_chapters || 0 }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="info-card">
            <div class="info-item">
              <span class="info-label">平均每本章节数：</span>
              <span class="info-value">{{ overview.avg_chapters_per_novel || 0 }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="info-card">
            <div class="info-item">
              <span class="info-label">待解析小说：</span>
              <span class="info-value">{{ pending.unparsed_novels || 0 }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- Novel Distribution Chart -->
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

    <!-- Top 50 Hot Roles Table -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>热门角色 TOP 50</span>
        </div>
      </template>
      <el-table :data="topRoles" v-loading="loading" stripe>
        <el-table-column prop="role_name" label="角色名" width="120" />
        <el-table-column prop="novel_name" label="小说名" min-width="150" show-overflow-tooltip />
        <el-table-column prop="role_count" label="引用次数" width="100" />
        <el-table-column label="性别" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.gender" :type="row.gender === '男' ? 'info' : 'danger'" size="small">
              {{ row.gender }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="绑定状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_bind" type="success" size="small">已绑定</el-tag>
            <el-tag v-else type="warning" size="small">未绑定</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="出场率" width="100">
          <template #default="{ row }">
            {{ row.presence_rate ? (row.presence_rate * 100).toFixed(1) + '%' : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Reading, User, Microphone, Warning } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import api from '@/api'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const loading = ref(false)
const overview = ref({})
const pending = ref({})
const novels = ref([])
const topRoles = ref([])

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

const getStateType = (state) => {
  const types = { 1: 'info', 2: 'warning', 3: 'success' }
  return types[state] || 'info'
}

const getStateName = (state) => {
  const names = { 1: '已分片待解析', 2: '已解析待合成', 3: '已合成语音' }
  return names[state] || '未知'
}

const loadData = async () => {
  loading.value = true
  try {
    const [overviewData, pendingData, novelsData, topRolesData] = await Promise.all([
      api.getStatsOverview(),
      api.getStatsPending(),
      api.getStatsNovels(),
      api.getStatsTopRoles(50)
    ])

    overview.value = overviewData || {}
    pending.value = pendingData || {}
    novels.value = novelsData?.novels || []
    topRoles.value = topRolesData?.roles || []
  } catch (error) {
    console.error('加载统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  margin-right: 20px;
  padding: 15px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-novels .stat-icon {
  background-color: #e6f7ff;
  color: #1890ff;
}

.stat-roles .stat-icon {
  background-color: #f6ffed;
  color: #52c41a;
}

.stat-audios .stat-icon {
  background-color: #fff7e6;
  color: #fa8c16;
}

.stat-pending .stat-icon {
  background-color: #fff1f0;
  color: #ff4d4f;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.info-card {
  padding: 15px 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-label {
  font-size: 14px;
  color: #666;
}

.info-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.chart-card,
.table-card {
  margin-bottom: 20px;
}

.chart-container {
  min-height: 200px;
}
</style>
