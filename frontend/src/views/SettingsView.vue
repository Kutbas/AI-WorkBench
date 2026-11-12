<template>
  <div class="page-card" v-if="cfg">
    <div class="page-head">
      <h3>设置</h3>
      <span class="hint">保存在服务端 data/config.json，对所有页面即时生效</span>
    </div>

    <el-form label-width="130px" style="max-width: 720px">
      <el-divider content-position="left">DMXAPI（图像生成 + 文档解析共用）</el-divider>
      <el-form-item label="Base URL">
        <el-input v-model="cfg.dmxapi.base_url" />
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="cfg.dmxapi.api_key" show-password class="mono" />
      </el-form-item>

      <el-divider content-position="left">图像生成默认参数</el-divider>
      <el-row>
        <el-col :span="12">
          <el-form-item label="模型">
            <el-input v-model="cfg.imagegen.model" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="尺寸">
            <el-input v-model="cfg.imagegen.size" placeholder="2048x1152" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="质量">
            <el-select v-model="cfg.imagegen.quality" style="width: 100%">
              <el-option v-for="q in ['high', 'medium', 'low']" :key="q" :label="q" :value="q" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="张数 n">
            <el-input-number v-model="cfg.imagegen.n" :min="1" :max="4" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">腾讯云 COS 图床（v5）</el-divider>
      <el-form-item label="SecretId">
        <el-input v-model="cfg.cos.secret_id" class="mono" />
      </el-form-item>
      <el-form-item label="SecretKey">
        <el-input v-model="cfg.cos.secret_key" show-password class="mono" />
      </el-form-item>
      <el-row>
        <el-col :span="12">
          <el-form-item label="Bucket">
            <el-input v-model="cfg.cos.bucket" placeholder="graphbed-1331926955" class="mono" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="存储区域">
            <el-input v-model="cfg.cos.region" placeholder="ap-shanghai" class="mono" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="存储路径前缀">
        <el-input v-model="cfg.cos.prefix" placeholder="GraphBed/" class="mono" />
      </el-form-item>

      <el-divider content-position="left">访问口令</el-divider>
      <el-form-item label="口令">
        <el-input v-model="cfg.access_token" show-password placeholder="留空即关闭口令（仅建议开发模式）" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        <el-button :loading="testing" @click="testCos">测试 COS 连通</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { api, type AppConfig } from '../api'

const cfg = ref<AppConfig | null>(null)
const saving = ref(false)
const testing = ref(false)

onMounted(async () => {
  try {
    cfg.value = await api.get<AppConfig>('/api/settings')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '配置读取失败')
  }
})

async function save() {
  if (!cfg.value) return
  saving.value = true
  try {
    cfg.value = await api.put<AppConfig>('/api/settings', cfg.value)
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function testCos() {
  if (!cfg.value) return
  testing.value = true
  try {
    // 用表单当前值直接测（未保存也能测）
    const res = await api.post<{ message: string }>('/api/settings/test-cos', { cos: cfg.value.cos })
    ElMessage.success(res.message)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '测试失败')
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
}

.page-head h3 {
  margin: 0;
}

.hint {
  color: #909399;
  font-size: 12px;
}
</style>
