<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">AI-WorkBench</h2>
      <p class="subtitle">请输入访问口令</p>
      <el-form @submit.prevent="onLogin">
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            show-password
            placeholder="访问口令"
            size="large"
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onLogin">
          进入工作台
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api, setToken } from '../api'

const password = ref('')
const loading = ref(false)
const router = useRouter()
const route = useRoute()

async function onLogin() {
  if (!password.value) return
  loading.value = true
  try {
    const res = await api.post<{ ok: boolean; token: string }>('/api/auth/login', { password: password.value })
    setToken(res.token)
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 360px;
  text-align: center;
}

.title {
  margin: 8px 0 4px;
  color: var(--el-color-primary);
}

.subtitle {
  color: #909399;
  margin: 0 0 20px;
  font-size: 13px;
}
</style>
