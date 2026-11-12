import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router, { invalidateAuth } from './router'
import './style.css'

// 任意 API 返回 401：清 token、重置登录态缓存、回登录页
// 已在登录页则不再跳（如口令输错），redirect 只带非 login 页路径，避免嵌套
window.addEventListener('aiwb:unauthorized', () => {
  invalidateAuth()
  const current = router.currentRoute.value
  if (current.name === 'login') return
  const redirect = current.fullPath.startsWith('/login') ? undefined : current.fullPath
  router.push(redirect ? { name: 'login', query: { redirect } } : { name: 'login' })
})

createApp(App).use(ElementPlus, { locale: zhCn }).use(router).mount('#app')
