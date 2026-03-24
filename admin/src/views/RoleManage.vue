<template>
  <div class="role-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button type="primary" @click="handleCreate">添加角色</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="小说名">
          <el-input v-model="queryForm.novel_name" placeholder="输入小说名" clearable />
        </el-form-item>
        <el-form-item label="角色名">
          <el-input v-model="queryForm.role_name" placeholder="输入角色名" clearable />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="queryForm.gender" placeholder="选择性别" clearable>
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定状态">
          <el-select v-model="queryForm.is_bind" placeholder="选择状态" clearable>
            <el-option label="已绑定" :value="true" />
            <el-option label="未绑定" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="novel_name" label="小说名" min-width="120" />
        <el-table-column prop="role_name" label="角色名" min-width="100" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="role_count" label="出现次数" width="100" />
        <el-table-column prop="chapter_count" label="章节数" width="100" />
        <el-table-column label="出场率" width="100">
          <template #default="{ row }">
            {{ (row.presence_rate * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column label="绑定状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_bind ? 'success' : 'info'">
              {{ row.is_bind ? '已绑定' : '未绑定' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="bind_audio_name" label="绑定音频" min-width="120" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="handleBindAudio(row)">绑定音频</el-button>
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
        <el-form-item label="小说名" prop="novel_name">
          <el-input v-model="formData.novel_name" placeholder="请输入小说名" />
        </el-form-item>
        <el-form-item label="角色名" prop="role_name">
          <el-input v-model="formData.role_name" placeholder="请输入角色名" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="formData.gender" placeholder="选择性别">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="出现次数" prop="role_count">
          <el-input-number v-model="formData.role_count" :min="0" />
        </el-form-item>
        <el-form-item label="章节数" prop="chapter_count">
          <el-input-number v-model="formData.chapter_count" :min="0" />
        </el-form-item>
        <el-form-item label="出场率" prop="presence_rate">
          <el-input-number v-model="formData.presence_rate" :min="0" :precision="2" :step="0.01" />
        </el-form-item>
        <el-form-item label="是否绑定">
          <el-switch v-model="formData.is_bind" />
        </el-form-item>
        <el-form-item label="绑定音频名" v-if="formData.is_bind">
          <el-input v-model="formData.bind_audio_name" placeholder="请输入绑定音频名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="bindDialogVisible"
      title="绑定音频"
      width="500px"
    >
      <el-form :model="bindForm" label-width="100px">
        <el-form-item label="角色名">
          <span>{{ bindForm.role_name }}</span>
        </el-form-item>
        <el-form-item label="选择音频" prop="audio_name">
          <el-select
            v-model="bindForm.audio_name"
            placeholder="请选择音频"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="audio in availableAudios"
              :key="audio.role_name"
              :label="`${audio.role_name}，${audio.gender}`"
              :value="audio.role_name"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBindSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const tableData = ref([])
const availableAudios = ref([])
const dialogVisible = ref(false)
const bindDialogVisible = ref(false)
const dialogTitle = ref('添加角色')
const formRef = ref(null)

const queryForm = reactive({
  novel_name: '',
  role_name: '',
  gender: '',
  is_bind: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const formData = reactive({
  id: null,
  novel_name: '',
  role_name: '',
  role_count: 0,
  gender: '男',
  is_bind: false,
  bind_audio_name: '',
  chapter_count: 0,
  presence_rate: 0.0
})

const bindForm = reactive({
  id: null,
  role_name: '',
  audio_name: '',
  novel_name: ''
})

const formRules = {
  novel_name: [
    { required: true, message: '请输入小说名', trigger: 'blur' }
  ],
  role_name: [
    { required: true, message: '请输入角色名', trigger: 'blur' }
  ],
  gender: [
    { required: true, message: '请选择性别', trigger: 'change' }
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
    if (queryForm.novel_name) {
      params.novel_name = queryForm.novel_name
    }
    if (queryForm.role_name) {
      params.role_name = queryForm.role_name
    }
    if (queryForm.gender) {
      params.gender = queryForm.gender
    }
    if (queryForm.is_bind !== null && queryForm.is_bind !== '') {
      params.is_bind = queryForm.is_bind
    }

    const data = await api.getRoles(params)
    tableData.value = data

    const summary = await api.getRolesSummary()
    pagination.total = summary.total_roles
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

const loadAvailableAudios = async (novelName) => {
  try {
    const data = await api.getUnboundRoleAudios(novelName)
    availableAudios.value = data
  } catch (error) {
    console.error('加载未绑定音频列表失败:', error)
  }
}

const handleQuery = () => {
  pagination.page = 1
  loadData()
}

const handleReset = () => {
  queryForm.novel_name = ''
  queryForm.role_name = ''
  queryForm.gender = ''
  queryForm.is_bind = null
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
  dialogTitle.value = '添加角色'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑角色'
  Object.assign(formData, {
    id: row.id,
    novel_name: row.novel_name,
    role_name: row.role_name,
    role_count: row.role_count,
    gender: row.gender,
    is_bind: row.is_bind,
    bind_audio_name: row.bind_audio_name || '',
    chapter_count: row.chapter_count,
    presence_rate: row.presence_rate || 0.0
  })
  dialogVisible.value = true
}

const handleBindAudio = (row) => {
  Object.assign(bindForm, {
    id: row.id,
    role_name: row.role_name,
    audio_name: '',
    novel_name: row.novel_name
  })
  loadAvailableAudios(row.novel_name)
  bindDialogVisible.value = true
}

const handleBindSubmit = async () => {
  if (!bindForm.audio_name) {
    ElMessage.warning('请选择音频')
    return
  }

  try {
    // 确保roleId是整数类型
    const roleId = parseInt(bindForm.id, 10)
    if (isNaN(roleId)) {
      ElMessage.error('角色ID无效')
      return
    }
    await api.bindRoleAudio(roleId, bindForm.audio_name)
    ElMessage.success('绑定成功')
    bindDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('绑定失败:', error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色"${row.role_name}"吗?`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await api.deleteRole(row.id)
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
          await api.updateRole(formData.id, formData)
          ElMessage.success('更新成功')
        } else {
          await api.createRole(formData)
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
    role_name: '',
    role_count: 0,
    gender: '男',
    is_bind: false,
    bind_audio_name: '',
    chapter_count: 0,
    presence_rate: 0.0
  })
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.role-manage {
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
