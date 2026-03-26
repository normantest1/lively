import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default {
  // Novel APIs
  getNovels(params) {
    return apiClient.get('/novels', { params }).then(res => res.data)
  },
  getNovel(id) {
    return apiClient.get(`/novels/${id}`).then(res => res.data)
  },
  createNovel(data) {
    return apiClient.post('/novels', data).then(res => res.data)
  },
  updateNovel(id, data) {
    return apiClient.put(`/novels/${id}`, data).then(res => res.data)
  },
  deleteNovel(id) {
    return apiClient.delete(`/novels/${id}`)
  },
  deleteNovelByName(novelName) {
    return apiClient.delete(`/novels/by-name/${encodeURIComponent(novelName)}`).then(res => res.data)
  },
  uploadNovelsBatch(files) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    return apiClient.post('/novels/upload-batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }).then(res => res.data)
  },
  getNovelNamesList() {
    return apiClient.get('/novel/names').then(res => res.data)
  },
  batchAnalyzeNovel(novelName, threadCount, chapterCount) {
    return apiClient.post('/novels/batch-analyze', null, {
      params: {
        novel_name: novelName,
        thread_count: threadCount,
        chapter_count: chapterCount
      }
    }).then(res => res.data)
  },
  getNovelState(id) {
    return apiClient.get(`/novels/${id}/state`).then(res => res.data)
  },
  getMaxChapterCount(novelName) {
    return apiClient.get('/novel/max-chapter-count', {
      params: { novel_name: novelName }
    }).then(res => res.data)
  },
  batchGenerateNovel(novelName, chapterCount) {
    return apiClient.post('/novels/batch-generate', null, {
      params: {
        novel_name: novelName,
        chapter_count: chapterCount
      }
    }).then(res => res.data)
  },

  // Role APIs
  getRoles(params) {
    return apiClient.get('/roles', { params }).then(res => res.data)
  },
  getRole(id) {
    return apiClient.get(`/roles/${id}`).then(res => res.data)
  },
  createRole(data) {
    return apiClient.post('/roles', data).then(res => res.data)
  },
  updateRole(id, data) {
    return apiClient.put(`/roles/${id}`, data).then(res => res.data)
  },
  deleteRole(id) {
    return apiClient.delete(`/roles/${id}`)
  },
  bindRoleAudio(roleId, audioName) {
    return apiClient.post(`/roles/${roleId}/bind-audio`, { audio_name: audioName }).then(res => res.data)
  },
  getUnboundRoleAudios(novelName) {
    return apiClient.get('/role-audio/unbound', {
      params: { novel_name: novelName }
    }).then(res => res.data)
  },

  // NovelName APIs
  getNovelNames(params) {
    return apiClient.get('/novel-names', { params }).then(res => res.data)
  },
  getNovelName(id) {
    return apiClient.get(`/novel-names/${id}`).then(res => res.data)
  },
  createNovelName(data) {
    return apiClient.post('/novel-names', data).then(res => res.data)
  },
  updateNovelName(id, data) {
    return apiClient.put(`/novel-names/${id}`, data).then(res => res.data)
  },
  deleteNovelName(id) {
    return apiClient.delete(`/novel-names/${id}`)
  },

  // RoleAudio APIs
  getRoleAudios(params) {
    return apiClient.get('/role-audios', { params }).then(res => res.data)
  },
  getRoleAudio(id) {
    return apiClient.get(`/role-audios/${id}`).then(res => res.data)
  },
  createRoleAudio(data) {
    return apiClient.post('/role-audios', data).then(res => res.data)
  },
  updateRoleAudio(id, data) {
    return apiClient.put(`/role-audios/${id}`, data).then(res => res.data)
  },
  deleteRoleAudio(id) {
    return apiClient.delete(`/role-audios/${id}`)
  },
  refreshRoleAudiosBatch() {
    return apiClient.post('/role-audios/refresh-batch').then(res => res.data)
  },

  // Statistics APIs
  getNovelsSummary() {
    return apiClient.get('/statistics/novels-summary').then(res => res.data)
  },
  getRolesSummary() {
    return apiClient.get('/statistics/roles-summary').then(res => res.data)
  },

  // Settings APIs
  getSettings() {
    return apiClient.get('/settings').then(res => res.data)
  },
  saveSettings(data) {
    return apiClient.post('/settings', data).then(res => res.data)
  },

  // Scheduled Tasks APIs
  getScheduledTasks() {
    return apiClient.get('/scheduled-tasks').then(res => res.data)
  },
  createScheduledParseTask(data) {
    return apiClient.post('/scheduled-tasks/parse', data).then(res => res.data)
  },
  createScheduledGenerateTask(data) {
    return apiClient.post('/scheduled-tasks/generate', data).then(res => res.data)
  },
  deleteScheduledTask(jobId) {
    return apiClient.delete(`/scheduled-tasks/${jobId}`).then(res => res.data)
  },
  getParseTaskStatus() {
    return apiClient.get('/scheduled-tasks/status/parse').then(res => res.data)
  },
  getGenerateTaskStatus() {
    return apiClient.get('/scheduled-tasks/status/generate').then(res => res.data)
  },
  getScheduledTasksDetails() {
    return apiClient.get('/scheduled-tasks/details').then(res => res.data)
  },
  getScheduledTaskDetail(jobId) {
    return apiClient.get(`/scheduled-tasks/details/${jobId}`).then(res => res.data)
  },
  getScheduledTasksLogs(limit = 100) {
    return apiClient.get('/scheduled-tasks/logs', {
      params: { limit }
    }).then(res => res.data)
  },
  clearScheduledTasksLogs() {
    return apiClient.delete('/scheduled-tasks/logs').then(res => res.data)
  },
  getMaxChapters(novelName, currentState) {
    return apiClient.get('/novel/max-chapters', {
      params: {
        novel_name: novelName,
        current_state: currentState
      }
    }).then(res => res.data)
  }
}
