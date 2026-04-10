<template>
  <div class="scheduled-task-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>定时任务</span>
          <div>
            <el-button type="info" @click="handleRefreshJobs">刷新任务列表</el-button>
            <el-button type="success" @click="handleShowLogs">定时状态</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="task-tabs">
        <el-tab-pane label="定时批量解析" name="parse">
          <el-card class="task-card">
            <template #header>
              <span>定时批量解析设置</span>
            </template>
            <el-form :model="parseForm" label-width="140px">
              <el-form-item label="Cron表达式">
                <el-input
                  v-model="parseForm.cron"
                  placeholder="0 * * * * * * (秒 分 时 日 月 周 年)"
                  style="width: 400px"
                />
                <el-tooltip content="格式：秒 分 时 日 月 周 年，例如：0 0/5 * * * * * 表示每五分钟执行">
                  <el-icon style="margin-left: 8px; cursor: pointer;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </el-form-item>
              
              <el-form-item label="按导入顺序全部解析">
                <el-switch v-model="parseForm.parse_all" />
                <span style="margin-left: 10px; color: #909399; font-size: 12px;">
                  勾选后按创建时间升序解析所有current_state=1的小说，每次解析任务数量由"需要解析的章节"决定
                </span>
              </el-form-item>

              <el-form-item label="小说名" v-if="!parseForm.parse_all">
                <el-select
                  v-model="parseForm.novel_name"
                  filterable
                  placeholder="请选择小说名"
                  style="width: 400px"
                  @change="handleParseNovelChange"
                >
                  <el-option
                    v-for="item in novelNamesList"
                    :key="item.id"
                    :label="item.novel_name"
                    :value="item.novel_name"
                  />
                </el-select>
              </el-form-item>

              <el-form-item :label="parseForm.parse_all ? '解析章节数' : '需要解析的章节'">
                <el-input-number
                  v-model="parseForm.chapter_count"
                  :min="1"
                  :max="parseForm.parse_all ? undefined : (parseForm.max_chapters > 0 ? parseForm.max_chapters : undefined)"
                  style="width: 300px"
                />
                <el-button
                  v-if="!parseForm.parse_all"
                  type="primary"
                  style="margin-left: 10px"
                  @click="handleSetParseMax"
                  :disabled="!parseForm.novel_name"
                >
                  最大
                </el-button>
                <span style="margin-left: 10px; color: #909399;">
                  <template v-if="parseForm.parse_all">
                    每次触发时解析的小说数量
                  </template>
                  <template v-else>
                    最大可解析章节数：{{ parseForm.max_chapters }}
                  </template>
                </span>
              </el-form-item>
              
              <el-form-item label="线程数量">
                <el-input-number
                  v-model="parseForm.thread_count"
                  :min="1"
                  :max="32"
                  style="width: 300px"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="handleSetParseTask">设置</el-button>
                <el-button type="danger" @click="handleDeleteParseTask">删除任务</el-button>
                <el-tag 
                  :type="parseTaskStatus.running ? 'warning' : 'success'"
                  style="margin-left: 20px"
                >
                  {{ parseTaskStatus.running ? '任务执行中' : '空闲' }}
                </el-tag>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="音频生成" name="watchdog">
          <el-card class="task-card">
            <template #header>
              <span>音频生成设置</span>
            </template>
            <el-form :model="watchdogForm" label-width="140px">
              <el-form-item label="Cron表达式">
                <el-input
                  v-model="watchdogForm.cron"
                  placeholder="0 * * * * * * (秒 分 时 日 月 周 年)"
                  style="width: 400px"
                />
                <el-tooltip content="格式：秒 分 时 日 月 周 年，例如：0 */5 * * * * * 表示每5分钟执行">
                  <el-icon style="margin-left: 8px; cursor: pointer;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </el-form-item>

              <el-form-item label="小说名">
                <el-select
                  v-model="watchdogForm.novel_name"
                  filterable
                  placeholder="请选择小说名"
                  style="width: 400px"
                  @change="handleWatchdogNovelChange"
                >
                  <el-option
                    v-for="item in novelNamesList"
                    :key="item.id"
                    :label="item.novel_name"
                    :value="item.novel_name"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="需要生成的章节">
                <el-input-number
                  v-model="watchdogForm.chapter_count"
                  :min="1"
                  :max="watchdogForm.max_chapters > 0 ? watchdogForm.max_chapters : undefined"
                  style="width: 300px"
                />
                <el-button
                  type="primary"
                  style="margin-left: 10px"
                  @click="handleSetWatchdogMax"
                  :disabled="!watchdogForm.novel_name"
                >
                  最大
                </el-button>
                <span style="margin-left: 10px; color: #909399;">
                  最大可生成章节数：{{ watchdogForm.max_chapters }}
                </span>
              </el-form-item>

              <el-form-item label="线程数">
                <el-input-number
                  v-model="watchdogForm.thread_count"
                  :min="1"
                  :max="32"
                  style="width: 300px"
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="handleSetWatchdogTask">添加</el-button>
                <el-button type="danger" @click="handleDeleteWatchdogTask">删除任务</el-button>
                <el-tag
                  :type="watchdogTaskStatus.running ? 'warning' : 'success'"
                  style="margin-left: 20px"
                >
                  {{ watchdogTaskStatus.running ? '任务执行中' : '空闲' }}
                </el-tag>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <el-card class="task-list-card" style="margin-top: 20px;">
        <template #header>
          <span>当前定时任务列表</span>
        </template>
        <el-table :data="scheduledJobs" v-loading="loading" stripe>
          <el-table-column prop="id" label="任务ID" width="200" />
          <el-table-column prop="name" label="任务名称" min-width="200" />
          <el-table-column prop="next_run_time" label="下次执行时间" width="200">
            <template #default="{ row }">
              {{ row.next_run_time ? formatDateTime(row.next_run_time) : 'N/A' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleShowDetail(row)">详情</el-button>
              <el-button link type="danger" @click="handleDeleteJob(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>

    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="700px"
    >
      <el-descriptions :column="2" border v-if="taskDetail">
        <el-descriptions-item label="任务ID">{{ taskDetail.job_id }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">{{ taskDetail.job_type === 'parse' ? '解析任务' : '生成任务' }}</el-descriptions-item>
        <el-descriptions-item label="任务名称" :span="2">{{ taskDetail.name }}</el-descriptions-item>
        <el-descriptions-item label="小说名称">{{ taskDetail.novel_name }}</el-descriptions-item>
        <el-descriptions-item label="章节数量">{{ taskDetail.chapter_count }}</el-descriptions-item>
        <el-descriptions-item label="线程数量" v-if="taskDetail.job_type === 'parse'">{{ taskDetail.thread_count }}</el-descriptions-item>
        <el-descriptions-item label="Cron表达式" :span="2">{{ taskDetail.cron }}</el-descriptions-item>
        <el-descriptions-item label="触发器" :span="2">
          <code>{{ taskDetail.trigger }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="最近5次执行时间" :span="2">
          <ul style="margin: 0; padding-left: 20px;">
            <li v-for="(time, index) in taskDetail.next_run_times" :key="index">
              {{ time }}
            </li>
            <li v-if="!taskDetail.next_run_times || taskDetail.next_run_times.length === 0" style="color: #909399;">
              暂无执行计划
            </li>
          </ul>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="logsDialogVisible"
      title="定时任务执行日志"
      width="900px"
      :close-on-click-modal="false"
    >
      <div class="logs-container">
        <div class="logs-toolbar">
          <el-button type="danger" size="small" @click="handleClearLogs">清空日志</el-button>
          <el-button type="primary" size="small" @click="handleRefreshLogs">刷新</el-button>
        </div>
        <el-input
          v-model="taskLogs"
          type="textarea"
          :rows="20"
          readonly
          placeholder="暂无日志..."
          style="font-family: monospace; font-size: 12px;"
        />
      </div>
      <template #footer>
        <el-button @click="logsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import api from '@/api'

const activeTab = ref('parse')
const loading = ref(false)
const scheduledJobs = ref([])
const novelNamesList = ref([])
const detailDialogVisible = ref(false)
const logsDialogVisible = ref(false)
const taskDetail = ref(null)
const taskLogs = ref('')
let logsRefreshTimer = null

const parseForm = reactive({
  cron: '0 0 2 * * * *',
  novel_name: '',
  chapter_count: 10,
  thread_count: 4,
  max_chapters: 0,
  parse_all: false
})

const watchdogForm = reactive({
  cron: '0 */5 * * * * *',
  novel_name: '',
  chapter_count: 1,
  thread_count: 1,
  max_chapters: 0
})

const watchdogTaskStatus = reactive({
  running: false
})

const loadNovelNames = async () => {
  try {
    const response = await api.getNovelNamesList()
    if (Array.isArray(response)) {
      novelNamesList.value = response.map((name, index) => ({
        id: index + 1,
        novel_name: name
      }))
    } else if (response.novel_names && Array.isArray(response.novel_names)) {
      novelNamesList.value = response.novel_names.map((name, index) => ({
        id: index + 1,
        novel_name: name
      }))
    } else {
      novelNamesList.value = []
    }
  } catch (error) {
    console.error('加载小说名列表失败:', error)
    ElMessage.error('加载小说名列表失败')
    novelNamesList.value = []
  }
}

const loadScheduledJobs = async () => {
  loading.value = true
  try {
    const response = await api.getScheduledTasks()
    if (response.jobs) {
      scheduledJobs.value = response.jobs
    } else {
      scheduledJobs.value = []
    }
  } catch (error) {
    console.error('加载定时任务列表失败:', error)
    ElMessage.error('加载定时任务列表失败')
    scheduledJobs.value = []
  } finally {
    loading.value = false
  }
}

const loadParseTaskStatus = async () => {
  try {
    const response = await api.getParseTaskStatus()
    parseTaskStatus.running = response.running
  } catch (error) {
    console.error('获取解析任务状态失败:', error)
  }
}

const loadWatchdogTaskStatus = async () => {
  try {
    const response = await api.getWatchdogTaskStatus()
    watchdogTaskStatus.running = response.running
  } catch (error) {
    console.error('获取看门狗任务状态失败:', error)
  }
}

const handleWatchdogNovelChange = async () => {
  if (watchdogForm.novel_name) {
    try {
      const response = await api.getMaxChapters(watchdogForm.novel_name, 2)
      watchdogForm.max_chapters = response.max_chapters
      watchdogForm.chapter_count = Math.min(watchdogForm.chapter_count, watchdogForm.max_chapters)
    } catch (error) {
      console.error('获取最大章节数失败:', error)
      watchdogForm.max_chapters = 0
    }
  } else {
    watchdogForm.max_chapters = 0
  }
}

const handleSetWatchdogMax = () => {
  if (watchdogForm.max_chapters) {
    watchdogForm.chapter_count = watchdogForm.max_chapters
  }
}

const handleSetWatchdogTask = async () => {
  if (!watchdogForm.cron) {
    ElMessage.warning('请填写Cron表达式')
    return
  }

  if (!watchdogForm.novel_name) {
    ElMessage.warning('请选择小说名')
    return
  }

  try {
    const response = await api.createScheduledWatchdogTask({
      job_id: `watchdog_${watchdogForm.novel_name}`,
      cron: watchdogForm.cron,
      novel_name: watchdogForm.novel_name,
      chapter_count: watchdogForm.chapter_count,
      thread_count: watchdogForm.thread_count
    })

    if (response.status === 'success') {
      ElMessage.success('看门狗任务设置成功')
      await loadScheduledJobs()
    } else {
      ElMessage.error('看门狗任务设置失败')
    }
  } catch (error) {
    console.error('设置看门狗任务失败:', error)
    ElMessage.error('设置看门狗任务失败')
  }
}

const handleDeleteWatchdogTask = async () => {
  if (!watchdogForm.novel_name) {
    ElMessage.warning('请先选择小说名')
    return
  }

  const jobId = `watchdog_${watchdogForm.novel_name}`

  try {
    await ElMessageBox.confirm('确定要删除看门狗任务吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const response = await api.deleteScheduledTask(jobId)
    if (response.status === 'success') {
      ElMessage.success('看门狗任务删除成功')
      await loadScheduledJobs()
    } else {
      ElMessage.error('看门狗任务删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除看门狗任务失败:', error)
      ElMessage.error('删除看门狗任务失败')
    }
  }
}

const handleParseNovelChange = async () => {
  if (parseForm.novel_name) {
    try {
      const response = await api.getMaxChapters(parseForm.novel_name, 1)
      parseForm.max_chapters = response.max_chapters
      parseForm.chapter_count = Math.min(parseForm.chapter_count, parseForm.max_chapters)
    } catch (error) {
      console.error('获取最大章节数失败:', error)
      parseForm.max_chapters = 0
    }
  } else {
    parseForm.max_chapters = 0
  }
}

const handleSetParseMax = () => {
  parseForm.chapter_count = parseForm.max_chapters
}

const handleSetParseTask = async () => {
  if (!parseForm.cron) {
    ElMessage.warning('请填写Cron表达式')
    return
  }
  if (!parseForm.parse_all && !parseForm.novel_name) {
    ElMessage.warning('请选择小说名或勾选全部解析')
    return
  }
  if (parseForm.parse_all && !parseForm.chapter_count) {
    ElMessage.warning('请填写解析章节数')
    return
  }
  if (!parseForm.parse_all && !parseForm.chapter_count) {
    ElMessage.warning('请填写需要解析的章节数')
    return
  }

  try {
    const response = await api.createScheduledParseTask({
      job_id: parseForm.parse_all ? 'parse_all' : `parse_${parseForm.novel_name}`,
      cron: parseForm.cron,
      novel_name: parseForm.parse_all ? '' : parseForm.novel_name,
      chapter_count: parseForm.chapter_count,
      thread_count: parseForm.thread_count
    })

    if (response.status === 'success') {
      ElMessage.success('定时解析任务设置成功')
      await loadScheduledJobs()
    } else {
      ElMessage.error('定时解析任务设置失败')
    }
  } catch (error) {
    console.error('设置定时解析任务失败:', error)
    ElMessage.error('设置定时解析任务失败')
  }
}

const handleDeleteParseTask = async () => {
  const jobId = parseForm.parse_all ? 'parse_all' : `parse_${parseForm.novel_name}`
  if (!parseForm.parse_all && !parseForm.novel_name) {
    ElMessage.warning('请先选择小说或勾选全部解析')
    return
  }

  try {
    await ElMessageBox.confirm('确定要删除该定时解析任务吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const response = await api.deleteScheduledTask(jobId)
    if (response.status === 'success') {
      ElMessage.success('定时解析任务删除成功')
      await loadScheduledJobs()
    } else {
      ElMessage.error('定时解析任务删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除定时解析任务失败:', error)
      ElMessage.error('删除定时解析任务失败')
    }
  }
}

const handleDeleteJob = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该定时任务吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const response = await api.deleteScheduledTask(row.id)
    if (response.status === 'success') {
      ElMessage.success('定时任务删除成功')
      await loadScheduledJobs()
    } else {
      ElMessage.error('定时任务删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除定时任务失败:', error)
      ElMessage.error('删除定时任务失败')
    }
  }
}

const handleShowDetail = async (row) => {
  try {
    const response = await api.getScheduledTaskDetail(row.id)
    taskDetail.value = response
    detailDialogVisible.value = true
  } catch (error) {
    console.error('获取任务详情失败:', error)
    ElMessage.error('获取任务详情失败')
  }
}

const handleShowLogs = async () => {
  logsDialogVisible.value = true
  await handleRefreshLogs()
  
  logsRefreshTimer = setInterval(async () => {
    if (logsDialogVisible.value) {
      await handleRefreshLogs()
    }
  }, 3000)
}

const handleRefreshLogs = async () => {
  try {
    const response = await api.getScheduledTasksLogs(200)
    if (response.logs) {
      taskLogs.value = response.logs.join('\n')
    }
  } catch (error) {
    console.error('获取日志失败:', error)
  }
}

const handleClearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有日志吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.clearScheduledTasksLogs()
    taskLogs.value = ''
    ElMessage.success('日志已清空')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空日志失败:', error)
      ElMessage.error('清空日志失败')
    }
  }
}

const handleRefreshJobs = async () => {
  await loadScheduledJobs()
  await loadParseTaskStatus()
  await loadWatchdogTaskStatus()
  ElMessage.success('刷新成功')
}

const formatDateTime = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(async () => {
  await loadNovelNames()
  await loadScheduledJobs()
  await loadParseTaskStatus()
  await loadWatchdogTaskStatus()

  setInterval(async () => {
    await loadParseTaskStatus()
    await loadWatchdogTaskStatus()
  }, 5000)
})

onUnmounted(() => {
  if (logsRefreshTimer) {
    clearInterval(logsRefreshTimer)
  }
})
</script>

<style scoped>
.scheduled-task-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-tabs {
  margin-bottom: 20px;
}

.task-card {
  margin-top: 10px;
}

.task-list-card {
  margin-top: 20px;
}

.logs-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.logs-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-descriptions) {
  font-size: 14px;
}

code {
  background-color: #f5f5f5;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}
</style>
