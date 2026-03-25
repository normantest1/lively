import { createRouter, createWebHistory } from 'vue-router'
import NovelManage from '@/views/NovelManage.vue'
import NovelNameManage from '@/views/NovelNameManage.vue'
import RoleManage from '@/views/RoleManage.vue'
import RoleAudioManage from '@/views/RoleAudioManage.vue'
import SettingsView from '@/views/SettingsView.vue'
import ScheduledTaskView from '@/views/ScheduledTaskView.vue'

const routes = [
  {
    path: '/',
    redirect: '/novels'
  },
  {
    path: '/novels',
    name: 'NovelManage',
    component: NovelManage,
    meta: { title: '小说管理' }
  },
  {
    path: '/novel-names',
    name: 'NovelNameManage',
    component: NovelNameManage,
    meta: { title: '小说名管理' }
  },
  {
    path: '/roles',
    name: 'RoleManage',
    component: RoleManage,
    meta: { title: '角色管理' }
  },
  {
    path: '/role-audios',
    name: 'RoleAudioManage',
    component: RoleAudioManage,
    meta: { title: '角色音频管理' }
  },
  {
    path: '/settings',
    name: 'SettingsView',
    component: SettingsView,
    meta: { title: '系统设置' }
  },
  {
    path: '/scheduled-tasks',
    name: 'ScheduledTaskView',
    component: ScheduledTaskView,
    meta: { title: '定时任务' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
