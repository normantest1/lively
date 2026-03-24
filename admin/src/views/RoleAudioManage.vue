<template>
  <div class="role-audio-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色音频管理</span>
          <div>
            <el-button type="primary" @click="handleCreate">添加音频</el-button>
            <el-button type="warning" @click="handleRefreshBatch">批量刷新后端角色</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="音频角色名">
          <el-input v-model="queryForm.role_name" placeholder="输入角色名" clearable />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="queryForm.gender" placeholder="选择性别" clearable>
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="最低引用次数">
          <el-input-number
            v-model="queryForm.min_citation_count"
            :min="0"
            placeholder="最低引用次数"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="role_name" label="音频角色名" min-width="120" />
        <el-table-column label="音频播放" width="100">
          <template #default="{ row }">
            <el-button
              :type="currentPlayingId === row.id ? 'warning' : 'primary'"
              circle
              @click="togglePlay(row)"
              :disabled="!row.audio_path"
              style="min-width: 36px; padding: 8px;"
            >
              <span v-if="currentPlayingId === row.id" style="font-size: 18px; font-weight: bold;">❚❚</span>
              <span v-else style="font-size: 18px;">▶</span>
            </el-button>
            <audio
              v-if="currentPlayingId === row.id"
              ref="audioRef"
              :src="getAudioUrl(row)"
              @ended="handleAudioEnded"
              @error="handleAudioError"
              style="display: none"
            />
          </template>
        </el-table-column>
        <el-table-column prop="audio_path" label="音频路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="citation_count" label="引用次数" width="100" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
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
        <el-form-item label="音频角色名" prop="role_name">
          <el-input v-model="formData.role_name" placeholder="请输入音频角色名" />
        </el-form-item>
        <el-form-item label="音频路径" prop="audio_path">
          <el-input v-model="formData.audio_path" placeholder="请输入音频文件路径" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="formData.gender" placeholder="选择性别">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="音频文本内容" prop="audio_text">
          <el-input
            v-model="formData.audio_text"
            type="textarea"
            :rows="4"
            placeholder="请输入音频的文本内容"
          />
        </el-form-item>
        <el-form-item label="引用次数" prop="citation_count">
          <el-input-number v-model="formData.citation_count" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
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
const dialogTitle = ref('添加音频')
const formRef = ref(null)
const audioRef = ref(null)
const currentPlayingId = ref(null)
const currentAudio = ref(null)

const queryForm = reactive({
  role_name: '',
  gender: '',
  min_citation_count: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const getAudioUrl = (row) => {
  if (!row) return ''

  // 优先使用 audio_uri
  if (row.audio_uri) {
    return `/audios/${row.audio_uri}`
  }

  // 如果没有 audio_uri，回退使用 audio_path
  if (row.audio_path) {
    if (row.audio_path.startsWith('http://') || row.audio_path.startsWith('https://')) {
      return row.audio_path
    }
    return `/api/audio/${encodeURIComponent(row.audio_path)}`
  }

  return ''
}

const togglePlay = async (row) => {
  if (!row.audio_path) {
    ElMessage.warning('该音频没有有效的路径')
    return
  }

  if (currentPlayingId.value === row.id) {
    if (currentAudio.value) {
      if (currentAudio.value.paused) {
        currentAudio.value.play()
      } else {
        currentAudio.value.pause()
        currentPlayingId.value = null
      }
    }
  } else {
    if (currentAudio.value) {
      currentAudio.value.pause()
    }
    currentPlayingId.value = row.id
    await nextTick()
    const audio = new Audio(getAudioUrl(row))
    currentAudio.value = audio
    audio.play()
    audio.onended = () => {
      currentPlayingId.value = null
      currentAudio.value = null
    }
    audio.onerror = () => {
      ElMessage.error('音频加载失败，请检查音频路径是否正确')
      currentPlayingId.value = null
      currentAudio.value = null
    }
  }
}

const handleAudioEnded = () => {
  currentPlayingId.value = null
  currentAudio.value = null
}

const handleAudioError = () => {
  ElMessage.error('音频播放失败')
  currentPlayingId.value = null
  currentAudio.value = null
}

const formData = reactive({
  id: null,
  role_name: '',
  audio_path: '',
  gender: '男',
  audio_text: '',
  citation_count: 0
})

const formRules = {
  role_name: [
    { required: true, message: '请输入音频角色名', trigger: 'blur' }
  ],
  audio_path: [
    { required: true, message: '请输入音频路径', trigger: 'blur' }
  ],
  gender: [
    { required: true, message: '请选择性别', trigger: 'change' }
  ],
  audio_text: [
    { required: true, message: '请输入音频文本内容', trigger: 'blur' }
  ]
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
      limit: pagination.pageSize
    }
    if (queryForm.role_name) {
      params.role_name = queryForm.role_name
    }
    if (queryForm.gender) {
      params.gender = queryForm.gender
    }
    if (queryForm.min_citation_count !== null && queryForm.min_citation_count > 0) {
      params.min_citation_count = queryForm.min_citation_count
    }

    const data = await api.getRoleAudios(params)
    tableData.value = data
    pagination.total = data.length
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
  queryForm.role_name = ''
  queryForm.gender = ''
  queryForm.min_citation_count = null
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

const handleCreate = () => {
  dialogTitle.value = '添加音频'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑音频'
  Object.assign(formData, {
    id: row.id,
    role_name: row.role_name,
    audio_path: row.audio_path,
    gender: row.gender,
    audio_text: row.audio_text || '',
    citation_count: row.citation_count
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除音频"${row.role_name}"吗?`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await api.deleteRoleAudio(row.id)
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
          await api.updateRoleAudio(formData.id, formData)
          ElMessage.success('更新成功')
        } else {
          await api.createRoleAudio(formData)
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
    role_name: '',
    audio_path: '',
    gender: '男',
    audio_text: '',
    citation_count: 0
  })
}

const handleRefreshBatch = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要批量刷新后端角色音频吗?',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    loading.value = true
    await api.refreshRoleAudiosBatch()
    ElMessage.success('批量刷新成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量刷新失败:', error)
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.role-audio-manage {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-form {
  margin-bottom: 20px;
}
</style>
