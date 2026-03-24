<template>
  <div class="settings-view">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="180px"
        style="max-width: 800px"
      >
        <el-form-item label="数据库名" prop="database_name">
          <el-input
            v-model="formData.database_name"
            placeholder="请输入数据库名"
          />
        </el-form-item>

        <el-form-item label="最大分片长度" prop="max_section_length">
          <el-input-number
            v-model="formData.max_section_length"
            :min="100"
            :max="100000"
            :step="100"
            style="width: 100%"
          />
        </el-form-item>

        <el-divider content-position="left">API 配置</el-divider>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="请输入 API Key"
            show-password
          />
        </el-form-item>

        <el-form-item label="Base URL" prop="base_url">
          <el-input
            v-model="formData.base_url"
            placeholder="请输入 Base URL"
          />
        </el-form-item>

        <el-form-item label="模型名称" prop="model_name">
          <el-input
            v-model="formData.model_name"
            placeholder="请输入模型名称"
          />
        </el-form-item>

        <el-form-item label="最大 Token" prop="max_token">
          <el-input-number
            v-model="formData.max_token"
            :min="100"
            :max="100000"
            :step="100"
            style="width: 100%"
          />
        </el-form-item>

        <el-divider content-position="left">其他设置</el-divider>

        <el-form-item label="预加载角色个数" prop="preload_role_count">
          <el-input-number
            v-model="formData.preload_role_count"
            :min="1"
            :max="100"
            :step="1"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">保存设置</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const saving = ref(false)
const formRef = ref(null)

const formData = reactive({
  database_name: 'novels.db',
  max_section_length: 3000,
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model_name: 'gpt-3.5-turbo',
  max_token: 2000,
  preload_role_count: 5
})

const formRules = {
  database_name: [
    { required: true, message: '请输入数据库名', trigger: 'blur' }
  ],
  max_section_length: [
    { required: true, message: '请输入最大分片长度', trigger: 'blur' }
  ],
  api_key: [
    { required: true, message: '请输入 API Key', trigger: 'blur' }
  ],
  base_url: [
    { required: true, message: '请输入 Base URL', trigger: 'blur' }
  ],
  model_name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' }
  ],
  max_token: [
    { required: true, message: '请输入最大 Token', trigger: 'blur' }
  ],
  preload_role_count: [
    { required: true, message: '请输入预加载角色个数', trigger: 'blur' }
  ]
}

const loadSettings = async () => {
  loading.value = true
  try {
    const data = await api.getSettings()
    Object.assign(formData, {
      database_name: data.database_name || 'novels.db',
      max_section_length: data.max_section_length || 3000,
      api_key: data.api_key || '',
      base_url: data.base_url || 'https://api.openai.com/v1',
      model_name: data.model_name || 'gpt-3.5-turbo',
      max_token: data.max_token || 2000,
      preload_role_count: data.preload_role_count || 5
    })
  } catch (error) {
    console.error('加载设置失败:', error)
    ElMessage.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        await api.saveSettings(formData)
        ElMessage.success('设置保存成功')
      } catch (error) {
        console.error('保存设置失败:', error)
        ElMessage.error('保存设置失败')
      } finally {
        saving.value = false
      }
    }
  })
}

const handleReset = () => {
  loadSettings()
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-view {
  padding: 20px;
}

:deep(.el-divider__text) {
  background-color: #f0f2f5;
  color: #606266;
  font-weight: 600;
}
</style>
