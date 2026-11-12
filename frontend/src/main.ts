import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router, { invalidateAuth } from './router'
import './style.css'

// 任意 API 返回 401：清 token、重置登录态缓存、回登录页
window.addEventListener('aiwb:unauthorized', () => {
  invalidateAuth()
  router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
})

createApp(App).use(ElementPlus, { locale: zhCn }).use(router).mount('#app')
