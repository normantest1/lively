<template>
  <div class="novel-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>小说管理</span>
          <div>
            <el-button type="primary" @click="handleCreate">添加小说</el-button>
            <el-button type="info" @click="handleBatchUpdateState" :disabled="selectedRows.length === 0">
              批量修改状态 ({{ selectedRows.length }})
            </el-button>
            <el-button type="danger" @click="handleDeleteNovelData">删除小说相关数据</el-button>
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :multiple="true"
              accept=".txt"
              :limit="50"
              :on-change="handleFileChange"
              :on-exceed="handleExceed"
              :file-list="fileList"
              class="batch-upload"
            >
              <el-button type="success">批量上传TXT</el-button>
              <template #tip>
                <div class="el-upload__tip">支持上传多个txt文件</div>
              </template>
            </el-upload>
            <el-button type="primary" @click="handleUploadBatch">上传文件</el-button>
            <el-button type="info" @click="handleShowLog">解析状态</el-button>
            <el-button type="warning" @click="handleBatchAnalyze">批量解析</el-button>
            <el-button type="success" @click="handleBatchGenerate">批量生成</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="小说名">
          <el-input v-model="queryForm.novel_name" placeholder="输入小说名" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryForm.current_state" placeholder="选择状态" clearable>
            <el-option label="已分片待解析" :value="1" />
            <el-option label="已解析待合成" :value="2" />
            <el-option label="已合成语音" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="novel_name" label="小说名" min-width="150" />
        <el-table-column prop="chapter_names" label="章节名" min-width="200" show-overflow-tooltip />
        <el-table-column label="当前状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStateType(row.current_state)">
              {{ getStateName(row.current_state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="handleShowState(row)">状态</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; justify-content: flex-end;"
      />

      <!-- 执行状态显示区域 -->
      <el-card v-if="showLogArea" class="log-card" style="margin-top: 20px;">
        <template #header>
          <div class="card-header">
            <span>执行状态</span>
            <el-button type="danger" size="small" @click="showLogArea = false">关闭</el-button>
          </div>
        </template>
        <el-input
          v-model="logContent"
          type="textarea"
          :rows="10"
          readonly
          placeholder="等待执行..."
          style="font-family: monospace; font-size: 12px;"
        />
      </el-card>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="小说名" prop="novel_name">
          <el-input v-model="formData.novel_name" placeholder="请输入小说名" />
        </el-form-item>
        <el-form-item label="章节名" prop="chapter_names">
          <el-input
            v-model="formData.chapter_names"
            type="textarea"
            :rows="3"
            placeholder="请输入章节名"
          />
        </el-form-item>
        <el-form-item label="分片数据" prop="section_data_json">
          <el-input
            v-model="formData.section_data_json"
            type="textarea"
            :rows="4"
            placeholder="请输入分片数据"
          />
        </el-form-item>
        <el-form-item label="解析后数据" prop="after_analysis_data_json">
          <el-input
            v-model="formData.after_analysis_data_json"
            type="textarea"
            :rows="4"
            placeholder="请输入解析后数据"
          />
        </el-form-item>
        <el-form-item label="当前状态" prop="current_state">
          <el-select v-model="formData.current_state" placeholder="选择状态">
            <el-option label="已分片待解析" :value="1" />
            <el-option label="已解析待合成" :value="2" />
            <el-option label="已合成语音" :value="3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 状态消息对话框 -->
    <el-dialog
      v-model="stateDialogVisible"
      title="状态消息"
      width="600px"
    >
      <el-input
        v-model="stateMessage"
        type="textarea"
        :rows="10"
        readonly
        placeholder="暂无消息..."
        style="font-family: monospace; font-size: 12px;"
      />
      <template #footer>
        <el-button @click="handleClearState">清空</el-button>
        <el-button type="primary" @click="stateDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 批量生成对话框 -->
    <el-dialog
      v-model="generateDialogVisible"
      title="批量生成小说"
      width="600px"
    >
      <el-form :model="generateForm" label-width="120px">
        <el-form-item label="选择小说" required>
          <el-select
            v-model="generateForm.novel_name"
            placeholder="请选择小说"
            filterable
            style="width: 100%"
            @change="handleNovelNameChange"
          >
            <el-option
              v-for="name in novelNamesList"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="章节数" required>
          <el-input-number
            v-model="generateForm.chapter_count"
            :min="1"
            :max="generateForm.max_chapter_count || 9999"
            style="width: 100%"
          />
          <el-button
            type="text"
            style="margin-left: 10px;"
            @click="handleSetMaxChapter"
          >
            最大: {{ generateForm.max_chapter_count || '—' }}
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleGenerateSubmit">开始生成</el-button>
      </template>
    </el-dialog>

    <!-- 批量解析对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量解析小说"
      width="600px"
    >
      <el-form :model="batchForm" label-width="120px">
        <el-form-item label="选择小说" required>
          <el-select
            v-model="batchForm.novel_name"
            placeholder="请选择小说"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="name in novelNamesList"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="线程数" required>
          <el-input-number
            v-model="batchForm.thread_count"
            :min="1"
            :max="32"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="章节数" required>
          <el-input-number
            v-model="batchForm.chapter_count"
            :min="1"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchSubmit">开始解析</el-button>
      </template>
    </el-dialog>

    <!-- 批量修改状态对话框 -->
    <el-dialog
      v-model="batchStateDialogVisible"
      title="批量修改小说状态"
      width="600px"
    >
      <el-form :model="batchStateForm" label-width="140px">
        <el-form-item label="当前状态">
          <el-tag :type="getStateType(batchStateForm.current_state)" size="large">
            {{ getStateName(batchStateForm.current_state) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="修改为" required>
          <el-select
            v-model="batchStateForm.new_state"
            placeholder="请选择新状态"
            style="width: 100%"
          >
            <el-option
              v-for="state in availableStates"
              :key="state.value"
              :label="state.label"
              :value="state.value"
              :disabled="state.value === 1"
            />
          </el-select>
        </el-form-item>
        <el-alert
          v-if="batchStateForm.new_state === 1"
          title="降级操作警告"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 20px;"
        >
          <template #default>
            <div style="font-size: 14px; line-height: 1.6;">
              <p><strong>降级操作说明：</strong></p>
              <ul style="margin: 10px 0; padding-left: 20px;">
                <li>选中的 {{ selectedRows.length }} 条小说数据的 <code>after_analysis_data_json</code> 字段将置为空</li>
                <li>roles 表中对应小说名的角色数据的 <code>chapter_count</code> 将减少 {{ selectedRows.length }}</li>
              </ul>
            </div>
          </template>
        </el-alert>
        <el-alert
          v-if="batchStateForm.new_state === 3"
          title="升级操作说明"
          type="success"
          :closable="false"
          show-icon
          style="margin-top: 20px;"
        >
          <template #default>
            <div style="font-size: 14px; line-height: 1.6;">
              <p>选中的 {{ selectedRows.length }} 条小说数据将直接升级为"已合成语音"状态。</p>
            </div>
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="batchStateDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleConfirmBatchUpdate"
          :disabled="!batchStateForm.new_state"
          :loading="batchStateLoading"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除小说相关数据对话框 -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="删除小说相关数据"
      width="600px"
    >
      <el-form :model="deleteForm" label-width="140px">
        <el-form-item label="选择小说" required>
          <el-select
            v-model="deleteForm.novel_name"
            placeholder="请选择要删除的小说"
            filterable
            style="width: 100%"
            clearable
            @clear="handleClearDeleteForm"
          >
            <el-option
              v-for="name in novelNamesList"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-alert
          v-if="deleteForm.novel_name"
          title="危险操作警告"
          type="error"
          :closable="false"
          show-icon
          style="margin-top: 20px;"
        >
          <template #default>
            <div style="font-size: 14px; line-height: 1.6;">
              <p><strong>这将删除以下所有相关数据：</strong></p>
              <ul style="margin: 10px 0; padding-left: 20px;">
                <li>novel_names 表中该小说的记录</li>
                <li>novels 表中该小说的所有章节数据（原始数据、解析数据）</li>
                <li>roles 表中该小说的所有角色数据</li>
              </ul>
              <p style="color: #f56c6c; font-weight: bold;">此操作不可逆，请谨慎操作！</p>
            </div>
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          @click="handleConfirmDelete"
          :disabled="!deleteForm.novel_name"
          :loading="deleteLoading"
        >
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加小说')
const formRef = ref(null)
const uploadRef = ref(null)
const fileList = ref([])
const batchDialogVisible = ref(false)
const novelNamesList = ref([])
const showLogArea = ref(false)
const logContent = ref('')
let websocket = null

const selectedRows = ref([])
const batchStateDialogVisible = ref(false)
const batchStateLoading = ref(false)
const batchStateForm = reactive({
  current_state: null,
  new_state: null
})
const availableStates = ref([
  { value: 2, label: '已解析待合成' },
  { value: 3, label: '已合成语音' }
])

const deleteDialogVisible = ref(false)
const deleteLoading = ref(false)
const deleteForm = reactive({
  novel_name: ''
})

const stateDialogVisible = ref(false)
const stateMessage = ref('')

const generateDialogVisible = ref(false)
const generateForm = reactive({
  novel_name: '',
  chapter_count: 1,
  max_chapter_count: null
})

const batchForm = reactive({
  novel_name: '',
  thread_count: 1,
  chapter_count: 1
})

const queryForm = reactive({
  novel_name: '',
  current_state: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const formData = reactive({
  id: null,
  novel_name: '',
  chapter_names: '',
  section_data_json: '',
  after_analysis_data_json: '',
  current_state: 1
})

const formRules = {
  novel_name: [
    { required: true, message: '请输入小说名', trigger: 'blur' }
  ],
  chapter_names: [
    { required: true, message: '请输入章节名', trigger: 'blur' }
  ],
  section_data_json: [
    { required: true, message: '请输入分片数据', trigger: 'blur' }
  ],
  current_state: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

const getStateType = (state) => {
  const types = { 1: 'info', 2: 'warning', 3: 'success' }
  return types[state] || 'info'
}

const getStateName = (state) => {
  const names = { 1: '已分片待解析', 2: '已解析待合成', 3: '已合成语音' }
  return names[state] || '未知'
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return ''
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      order_by_create_time_desc: true
    }
    if (queryForm.novel_name) {
      params.novel_name = queryForm.novel_name
    }
    if (queryForm.current_state) {
      params.current_state = queryForm.current_state
    }

    const data = await api.getNovels(params)
    tableData.value = data

    const summary = await api.getNovelsSummary()
    pagination.total = summary.total_novels
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

const handleQuery = () => {
  pagination.page = 1
  loadData()
}

const handleReset = () => {
  queryForm.novel_name = ''
  queryForm.current_state = null
  handleQuery()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  loadData()
}

const handlePageChange = (page) => {
  pagination.page = page
  loadData()
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const handleBatchUpdateState = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要修改的小说')
    return
  }

  // 检查所有选中小说的状态是否相同
  const states = [...new Set(selectedRows.value.map(row => row.current_state))]

  // 如果状态不相同，不允许修改
  if (states.length !== 1) {
    ElMessage.warning('所选小说的状态不同，无法批量修改，请选择状态相同的小说')
    return
  }

  // 如果状态是1，不允许修改
  if (states[0] === 1) {
    ElMessage.warning('状态为"已分片待解析"的小说不允许修改状态')
    return
  }

  batchStateForm.current_state = states[0]
  batchStateForm.new_state = null
  batchStateDialogVisible.value = true
}

const handleConfirmBatchUpdate = async () => {
  if (!batchStateForm.new_state) {
    ElMessage.warning('请选择要修改的状态')
    return
  }

  try {
    batchStateLoading.value = true

    const novelIds = selectedRows.value.map(row => row.id)

    await api.batchUpdateNovelsState({
      novel_ids: novelIds,
      new_state: batchStateForm.new_state
    })

    ElMessage.success(`成功修改 ${novelIds.length} 条小说数据的状态`)
    batchStateDialogVisible.value = false
    selectedRows.value = []

    // 刷新数据
    await loadData()
  } catch (error) {
    console.error('批量修改状态失败:', error)
    ElMessage.error('批量修改状态失败: ' + (error.message || '未知错误'))
  } finally {
    batchStateLoading.value = false
  }
}

const handleCreate = () => {
  dialogTitle.value = '添加小说'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑小说'
  Object.assign(formData, {
    id: row.id,
    novel_name: row.novel_name,
    chapter_names: row.chapter_names || '',
    section_data_json: row.section_data_json || '',
    after_analysis_data_json: row.after_analysis_data_json || '',
    current_state: row.current_state
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除小说"${row.novel_name}"吗?`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await api.deleteNovel(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (formData.id) {
          await api.updateNovel(formData.id, formData)
          ElMessage.success('更新成功')
        } else {
          await api.createNovel(formData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadData()
      } catch (error) {
        console.error('操作失败:', error)
      }
    }
  })
}

const handleDialogClose = () => {
  resetForm()
  formRef.value?.resetFields()
}

const resetForm = () => {
  Object.assign(formData, {
    id: null,
    novel_name: '',
    chapter_names: '',
    section_data_json: '',
    after_analysis_data_json: '',
    current_state: 1
  })
}

const handleFileChange = async (file, files) => {
  const rawFile = file.raw
  if (!rawFile) return

  if (!rawFile.name.endsWith('.txt')) {
    ElMessage.error('只能上传 TXT 文件')
    uploadRef.value.handleRemove(file)
    return
  }

  fileList.value = files
}

const handleExceed = (files, uploadFiles) => {
  ElMessage.warning(`当前限制选择 50 个文件，本次选择了 ${files.length} 个文件，共选择了 ${files.length + uploadFiles.length} 个文件`)
}

const handleUploadBatch = async () => {
  if (!fileList.value || fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  try {
    loading.value = true
    const files = fileList.value.map(item => item.raw)

    await api.uploadNovelsBatch(files)
    ElMessage.success(`成功上传 ${files.length} 个文件`)
    fileList.value = []
    loadData()
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  loadNovelNames()
  connectWebSocket()
})

const loadNovelNames = async () => {
  try {
    const names = await api.getNovelNamesList()
    novelNamesList.value = names
  } catch (error) {
    console.error('加载小说列表失败:', error)
  }
}

const connectWebSocket = () => {
  // 如果已存在连接，先关闭
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    console.log('WebSocket已连接')
    return
  }

  try {
    websocket = new WebSocket('ws://localhost:6888/ws/logs')

    websocket.onopen = () => {
      console.log('WebSocket连接已建立')
      // 连接成功，发送心跳
      startHeartbeat()
    }

    websocket.onmessage = (event) => {
      // 忽略心跳消息
      if (event.data === '[HEARTBEAT]\n' || event.data === 'heartbeat_ack' || event.data === 'pong') {
        return
      }

      // 添加日志内容
      logContent.value += event.data
      nextTick(() => {
        const textarea = document.querySelector('.log-card textarea')
        if (textarea) {
          textarea.scrollTop = textarea.scrollHeight
        }
      })
    }

    websocket.onerror = (error) => {
      console.error('WebSocket错误:', error)
    }

    websocket.onclose = () => {
      console.log('WebSocket连接已关闭')
      stopHeartbeat()
      // 5秒后尝试重连
      setTimeout(() => {
        if (showLogArea.value) {
          connectWebSocket()
        }
      }, 5000)
    }
  } catch (error) {
    console.error('WebSocket连接失败:', error)
  }
}

// 心跳定时器
let heartbeatTimer = null

const startHeartbeat = () => {
  stopHeartbeat()
  // 每20秒发送一次心跳
  heartbeatTimer = setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send('heartbeat')
    }
  }, 20000)
}

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

const handleBatchAnalyze = async () => {
  batchDialogVisible.value = true
}

const handleBatchSubmit = async () => {
  if (!batchForm.novel_name) {
    ElMessage.warning('请选择小说')
    return
  }

  try {
    batchDialogVisible.value = false

    await api.batchAnalyzeNovel(
      batchForm.novel_name,
      batchForm.thread_count,
      batchForm.chapter_count
    )

    ElMessage.success('批量解析任务已提交')
  } catch (error) {
    console.error('批量解析失败:', error)
  }
}

const handleShowLog = () => {
  showLogArea.value = !showLogArea.value
  if (showLogArea.value) {
    nextTick(() => {
      connectWebSocket()
    })
  }
}

const handleShowState = async (row) => {
  stateDialogVisible.value = true
  stateMessage.value = '正在获取状态信息...'

  try {
    const response = await api.getNovelState(row.id)
    stateMessage.value = response.message || JSON.stringify(response, null, 2)
  } catch (error) {
    stateMessage.value = `获取状态失败: ${error.message || '未知错误'}`
  }
}

const handleClearState = () => {
  stateMessage.value = ''
}

const handleBatchGenerate = () => {
  generateForm.novel_name = ''
  generateForm.chapter_count = 1
  generateForm.max_chapter_count = null
  generateDialogVisible.value = true
}

const handleNovelNameChange = async (novelName) => {
  if (!novelName) return

  try {
    const maxCount = await api.getMaxChapterCount(novelName)
    generateForm.max_chapter_count = maxCount
    generateForm.chapter_count = 1
  } catch (error) {
    console.error('获取最大章节数失败:', error)
    generateForm.max_chapter_count = null
  }
}

const handleSetMaxChapter = () => {
  if (generateForm.max_chapter_count) {
    generateForm.chapter_count = generateForm.max_chapter_count
  }
}

const handleGenerateSubmit = async () => {
  if (!generateForm.novel_name) {
    ElMessage.warning('请选择小说')
    return
  }

  if (!generateForm.chapter_count || generateForm.chapter_count < 1) {
    ElMessage.warning('请输入有效的章节数')
    return
  }

  try {
    generateDialogVisible.value = false
    showLogArea.value = true
    nextTick(() => {
      connectWebSocket()
    })

    await api.batchGenerateNovel(
      generateForm.novel_name,
      generateForm.chapter_count
    )

    ElMessage.success('批量生成任务已提交')
  } catch (error) {
    console.error('批量生成失败:', error)
  }
}

const handleDeleteNovelData = () => {
  deleteForm.novel_name = ''
  deleteDialogVisible.value = true
}

const handleClearDeleteForm = () => {
  deleteForm.novel_name = ''
}

const handleConfirmDelete = async () => {
  if (!deleteForm.novel_name) {
    ElMessage.warning('请选择要删除的小说')
    return
  }

  try {
    await ElMessageBox.confirm(
      '这将删除导入小说的所有原始数据、解析数据、角色数据，还继续吗？继续的话请点击确认按钮',
      '危险操作确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'error'
      }
    )

    deleteLoading.value = true

    // 调用后端API删除小说所有相关数据
    await api.deleteNovelByName(deleteForm.novel_name)

    ElMessage.success(`成功删除小说 "${deleteForm.novel_name}" 的所有相关数据`)
    deleteDialogVisible.value = false

    // 刷新数据
    await loadData()
    await loadNovelNames()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除小说相关数据失败:', error)
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    deleteLoading.value = false
  }
}
</script>

<style scoped>
.novel-manage {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header > div:last-child {
  display: flex;
  align-items: center;
  gap: 10px;
}

.query-form {
  margin-bottom: 20px;
}

.batch-upload {
  display: inline-block;
}

:deep(.el-upload__tip) {
  margin-top: 0;
  color: #909399;
  font-size: 12px;
}
</style>
