import { createRouter, createWebHistory } from 'vue-router'
import { api, getToken } from './api'

import DefaultLayout from './layouts/DefaultLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: DefaultLayout,
    children: [
      { path: '', redirect: '/image-gen' },
      { path: 'image-gen', name: 'image-gen', component: () => import('./views/ImageGenView.vue'), meta: { title: '图像生成' } },
      { path: 'somark', name: 'somark', component: () => import('./views/SoMarkView.vue'), meta: { title: '文档解析' } },
      { path: 'text-clean', name: 'text-clean', component: () => import('./views/TextCleanView.vue'), meta: { title: '文本清洗' } },
      { path: 'settings', name: 'settings', component: () => import('./views/SettingsView.vue'), meta: { title: '设置' } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

let needAuth: boolean | null = null // 会话内缓存；401 时由 api.ts 重置 token 并跳转

router.beforeEach(async (to) => {
  if (needAuth === null) {
    try {
      const status = await api.get<{ need_auth: boolean }>('/api/auth/status')
      needAuth = status.need_auth
    } catch {
      needAuth = false // 后端不可达时放行，页面内请求会给出明确报错
    }
  }
  if (!to.meta.public && needAuth && !getToken()) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && (!needAuth || getToken())) {
    return { path: '/' }
  }
})

export function invalidateAuth(): void {
  needAuth = null
}

export default router
