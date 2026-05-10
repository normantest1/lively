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

        <el-form-item label="绑定音频的出场率" prop="bind_audio_presence_rate">
          <el-input-number
            v-model="formData.bind_audio_presence_rate"
            :min="0"
            :max="1"
            :step="0.1"
            :precision="2"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            当角色出场率大于此值时，自动绑定音频（值范围：0-1，例如：0.4 表示 40%）
          </div>
        </el-form-item>

        <el-divider content-position="left">看门狗设置</el-divider>

        <el-form-item label="RTF 重启阈值" prop="rtf_threshold">
          <el-input-number
            v-model="formData.rtf_threshold"
            :min="0"
            :max="2"
            :step="0.1"
            :precision="2"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            当 RTF 大于此值时自动重启模型（值范围：0-2）
          </div>
        </el-form-item>

        <el-form-item label="模型重载等待(秒)" prop="watchdog_reload_wait_seconds">
          <el-input-number
            v-model="formData.watchdog_reload_wait_seconds"
            :min="10"
            :max="300"
            :step="10"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="恢复任务等待(秒)" prop="watchdog_resume_wait_seconds">
          <el-input-number
            v-model="formData.watchdog_resume_wait_seconds"
            :min="10"
            :max="300"
            :step="10"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="日志检查行数" prop="watchdog_log_check_lines">
          <el-input-number
            v-model="formData.watchdog_log_check_lines"
            :min="5"
            :max="50"
            :step="5"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="自动恢复任务" prop="watchdog_auto_recovery">
          <el-switch v-model="formData.watchdog_auto_recovery" />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            开启后，系统重启时可自动恢复看门狗生成任务
          </div>
        </el-form-item>

        <el-divider content-position="left">音频生成设置</el-divider>

        <el-form-item label="推理步数" prop="inference_steps">
          <el-input-number
            v-model="formData.inference_steps"
            :min="4"
            :max="100"
            :step="1"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            音频生成的推理步数，值越大质量越高但速度越慢（范围：4-100）
          </div>
        </el-form-item>

        <el-form-item label="语音速度" prop="speech_speed">
          <el-input-number
            v-model="formData.speech_speed"
            :min="0.5"
            :max="2"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            语音生成的速度，值越大语速越快（范围：0.5-2）
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">保存设置</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>TTS 模型控制</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="模型状态">
          <el-tag :type="ttsStatus === 'loaded' ? 'success' : ttsStatus === 'loading' ? 'warning' : 'info'">
            {{ ttsStatus === 'loaded' ? '已加载' : ttsStatus === 'loading' ? '加载中...' : '已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模型名称">VoxCPM1.5</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 20px;">
        <el-button
          type="primary"
          :loading="ttsLoading"
          :disabled="ttsStatus !== 'stopped'"
          @click="handleLoadModel"
        >
          加载模型
        </el-button>
        <el-button
          type="danger"
          :loading="ttsLoading"
          :disabled="ttsStatus !== 'loaded'"
          @click="handleStopModel"
        >
          停止模型
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const saving = ref(false)
const formRef = ref(null)

const ttsStatus = ref('stopped')
const ttsLoading = ref(false)
let statusPollTimer = null

const formData = reactive({
  database_name: 'novels.db',
  max_section_length: 3000,
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model_name: 'gpt-3.5-turbo',
  max_token: 2000,
  preload_role_count: 5,
  bind_audio_presence_rate: 0.4,
  rtf_threshold: 0.8,
  watchdog_auto_recovery: true,
  watchdog_reload_wait_seconds: 60,
  watchdog_resume_wait_seconds: 120,
  watchdog_log_check_lines: 10,
  inference_steps: 6,
  speech_speed: 0.9
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
  ],
  bind_audio_presence_rate: [
    { required: true, message: '请输入绑定音频的出场率', trigger: 'blur' }
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
      preload_role_count: data.preload_role_count || 5,
      bind_audio_presence_rate: data.bind_audio_presence_rate || 0.4,
      rtf_threshold: data.rtf_threshold ?? 0.8,
      watchdog_auto_recovery: data.watchdog_auto_recovery ?? true,
      watchdog_reload_wait_seconds: data.watchdog_reload_wait_seconds ?? 60,
      watchdog_resume_wait_seconds: data.watchdog_resume_wait_seconds ?? 120,
      watchdog_log_check_lines: data.watchdog_log_check_lines ?? 10,
      inference_steps: data.inference_steps ?? 6,
      speech_speed: data.speech_speed ?? 0.9
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

const fetchTtsStatus = async () => {
  try {
    const data = await api.getTtsStatus()
    ttsStatus.value = data.status || (data.loaded ? 'loaded' : 'stopped')
  } catch (error) {
    console.error('获取TTS状态失败:', error)
  }
}

const handleLoadModel = async () => {
  ttsLoading.value = true
  ttsStatus.value = 'loading'
  try {
    const result = await api.loadTtsModel()
    if (result.success) {
      ElMessage.success(result.message)
      ttsStatus.value = 'loaded'
    } else {
      ElMessage.error(result.message)
      ttsStatus.value = 'stopped'
    }
  } catch (error) {
    ElMessage.error('加载模型失败')
    ttsStatus.value = 'stopped'
  } finally {
    ttsLoading.value = false
  }
}

const handleStopModel = async () => {
  ttsLoading.value = true
  try {
    const result = await api.stopTtsModel()
    if (result.success) {
      ElMessage.success(result.message)
      ttsStatus.value = 'stopped'
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error('停止模型失败')
  } finally {
    ttsLoading.value = false
  }
}

onMounted(() => {
  loadSettings()
  fetchTtsStatus()
  statusPollTimer = setInterval(fetchTtsStatus, 5000)
})

onUnmounted(() => {
  if (statusPollTimer) {
    clearInterval(statusPollTimer)
  }
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
