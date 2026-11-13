<template>
  <div class="page-card">
    <div class="page-head">
      <h3>图像生成</h3>
      <span class="hint">DMXAPI · 提示词原文直传 · 生成后自动上传图床</span>
    </div>

    <!-- 提示词卡片 -->
    <div v-for="(card, i) in cards" :key="i" class="prompt-card">
      <div class="prompt-head">
        <el-input v-model="card.name" placeholder="任务名（可选，用于文件名）" size="small" class="name-input" />
        <span class="index mono">#{{ i + 1 }}</span>
        <el-button
          v-if="cards.length > 1"
          :icon="Delete"
          circle
          size="small"
          title="删除此提示词"
          @click="cards.splice(i, 1)"
        />
      </div>
      <el-input v-model="card.prompt" type="textarea" :rows="6" placeholder="提示词（支持 Mermaid 草稿等长文本，原文直传）" />
    </div>
    <el-button type="primary" plain :icon="Plus" @click="cards.push({ name: '', prompt: '' })">再加一个提示词</el-button>

    <!-- 生成参数 -->
    <el-divider content-position="left">生成参数</el-divider>
    <el-form label-width="90px" class="params-form">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="模型">
            <el-input v-model="params.model" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="尺寸">
            <el-select v-model="params.size" filterable allow-create default-first-option style="width: 100%">
              <el-option label="2048x1152（16:9 横幅）" value="2048x1152" />
              <el-option label="1024x1024（1:1 方形）" value="1024x1024" />
              <el-option label="1152x2048（9:16 竖版）" value="1152x2048" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="质量">
            <el-select v-model="params.quality" style="width: 100%">
              <el-option v-for="q in ['high', 'medium', 'low']" :key="q" :label="q" :value="q" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="张数 n">
            <el-input-number v-model="params.n" :min="1" :max="4" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-collapse class="advanced">
        <el-collapse-item title="高级参数" name="adv">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="格式">
                <el-select v-model="params.output_format" style="width: 100%">
                  <el-option v-for="f in ['png', 'jpeg', 'webp']" :key="f" :label="f" :value="f" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="moderation">
                <el-select v-model="params.moderation" style="width: 100%">
                  <el-option v-for="m in ['low', 'auto']" :key="m" :label="m" :value="m" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="background">
                <el-select v-model="params.background" style="width: 100%">
                  <el-option v-for="b in ['auto', 'transparent', 'opaque']" :key="b" :label="b" :value="b" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="复制格式">
                <el-select v-model="linkFormat" style="width: 100%">
                  <el-option v-for="f in LINK_FORMATS" :key="f.value" :label="f.label" :value="f.value" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </el-collapse-item>
      </el-collapse>
      <el-button type="primary" size="large" :loading="submitting" @click="submit">
        开始生成（{{ cards.length }} 个提示词）
      </el-button>
    </el-form>

    <!-- 当前任务详情 -->
    <template v-if="job">
      <el-divider content-position="left">
        任务 {{ job.id }}
        <el-tag :type="statusTag(job.status)" size="small">{{ job.status }}</el-tag>
      </el-divider>
      <div v-for="(t, i) in job.tasks" :key="i" class="task-block">
        <div class="task-head">
          <b>{{ t.name }}</b>
          <el-tag :type="statusTag(t.status)" size="small">{{ t.status }}</el-tag>
          <span v-if="t.error" class="err">{{ t.error }}</span>
        </div>
        <div class="img-grid">
          <div v-for="(img, ii) in t.images ?? []" :key="img.filename" class="img-cell">
            <el-image :src="imgUrl(img.filename)" :preview-src-list="[imgUrl(img.filename)]" fit="contain" lazy />
            <div class="img-ops">
              <el-button link type="primary" size="small" @click="copyImage(t, img, ii)">复制{{ formatLabel }}</el-button>
              <a :href="imgUrl(img.filename)" :download="img.filename">
                <el-button link type="primary" size="small">下载</el-button>
              </a>
              <el-button
                v-if="img.upload_error"
                link
                type="warning"
                size="small"
                :loading="reuploading === img.filename"
                :title="img.upload_error"
                @click="doReupload(img.filename)"
              >
                重传图床
              </el-button>
            </div>
            <div v-if="img.upload_error" class="upload-err mono">{{ img.upload_error }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 历史 -->
    <el-divider content-position="left">
      历史任务
      <el-button link type="primary" size="small" style="margin-left: 8px" @click="refreshHistory">刷新</el-button>
    </el-divider>
    <el-table :data="history" size="small" @row-click="loadJob">
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column prop="id" label="任务 ID" width="240" class-name="mono" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="子任务">
        <template #default="{ row }">
          {{ row.tasks.map((t: SoMarkTask) => t.status).join(' / ') }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api, type Job, type SoMarkTask } from '../api'

interface PromptCard {
  name: string
  prompt: string
}

const cards = reactive<PromptCard[]>([{ name: '', prompt: '' }])

const params = reactive({
  model: 'gpt-image-2.5-sunburst-ssvip',
  size: '2048x1152',
  quality: 'high',
  n: 1,
  output_format: 'png',
  moderation: 'low',
  background: 'auto',
})

const submitting = ref(false)
const job = ref<Job | null>(null)
const history = ref<Job[]>([])
const reuploading = ref('')
let timer: number | undefined

function statusTag(s: string): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  if (s === 'done') return 'success'
  if (s === 'running') return 'primary'
  if (s === 'pending') return 'info'
  if (s === 'interrupted') return 'warning'
  return 'danger'
}

function imgUrl(filename: string): string {
  return `/api/files/images/${encodeURIComponent(filename)}`
}

// ---------- 图床链接多格式复制 ----------

type LinkFormat = 'url' | 'markdown' | 'html' | 'ubb'

const LINK_FORMATS: { value: LinkFormat; label: string }[] = [
  { value: 'url', label: 'URL（纯链接）' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'html', label: 'HTML' },
  { value: 'ubb', label: 'UBB' },
]

const LINK_FORMAT_KEY = 'aiwb_link_format'

function loadLinkFormat(): LinkFormat {
  const saved = localStorage.getItem(LINK_FORMAT_KEY)
  return LINK_FORMATS.some((f) => f.value === saved) ? (saved as LinkFormat) : 'url'
}

const linkFormat = ref<LinkFormat>(loadLinkFormat())
watch(linkFormat, (v) => localStorage.setItem(LINK_FORMAT_KEY, v))

const formatLabel = computed(() => LINK_FORMATS.find((f) => f.value === linkFormat.value)?.label.split('（')[0] ?? '')

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function formatLink(url: string, alt: string): string {
  switch (linkFormat.value) {
    case 'markdown':
      return `![${alt}](${url})`
    case 'html':
      return `<img src="${url}" alt="${escapeHtml(alt)}" />`
    case 'ubb':
      return `[img]${url}[/img]`
    default:
      return url
  }
}

async function copyImage(task: { name: string; images?: unknown[] }, img: { cos_url?: string }, imgIdx: number) {
  const url = img.cos_url
  if (!url) {
    ElMessage.warning('该图片尚未上传图床（可先点"重传图床"）')
    return
  }
  // 多图（n>1）时 alt 加序号区分
  const alt = (task.images?.length ?? 1) > 1 ? `${task.name}-${imgIdx + 1}` : task.name
  const text = formatLink(url, alt)
  await navigator.clipboard.writeText(text)
  ElMessage.success({ message: `已复制：${text.length > 60 ? text.slice(0, 60) + '…' : text}`, duration: 3000 })
}

onMounted(async () => {
  // 参数默认值跟随设置页
  try {
    const cfg = await api.get<{ imagegen: Record<string, unknown> }>('/api/settings')
    Object.assign(params, cfg.imagegen)
  } catch {
    /* 设置读取失败就用内置默认 */
  }
  await refreshHistory()
})

onBeforeUnmount(stopPolling)

async function refreshHistory() {
  try {
    history.value = await api.get<Job[]>('/api/imagegen/jobs')
  } catch {
    /* 忽略历史加载失败 */
  }
}

async function submit() {
  const valid = cards.filter((c) => c.prompt.trim())
  if (!valid.length) {
    ElMessage.warning('请至少填写一个提示词')
    return
  }
  submitting.value = true
  try {
    const res = await api.post<{ job_id: string }>('/api/imagegen/jobs', {
      tasks: valid.map((c) => ({ name: c.name, prompt: c.prompt })),
      params: { ...params },
    })
    job.value = await api.get<Job>(`/api/imagegen/jobs/${res.job_id}`)
    startPolling(res.job_id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

function startPolling(id: string) {
  stopPolling()
  timer = window.setInterval(async () => {
    try {
      const j = await api.get<Job>(`/api/imagegen/jobs/${id}`)
      job.value = j
      if (j.status !== 'running') {
        stopPolling()
        refreshHistory()
      }
    } catch {
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
}

async function loadJob(row: Job) {
  stopPolling()
  try {
    job.value = await api.get<Job>(`/api/imagegen/jobs/${row.id}`)
    if (job.value.status === 'running') startPolling(row.id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  }
}

async function doReupload(filename: string) {
  reuploading.value = filename
  try {
    const res = await api.post<{ cos_url: string }>(`/api/imagegen/images/${encodeURIComponent(filename)}/reupload`)
    ElMessage.success(`已上传：${res.cos_url}`)
    if (job.value) {
      for (const t of job.value.tasks) {
        for (const img of t.images ?? []) {
          if (img.filename === filename) {
            img.cos_url = res.cos_url
            delete img.upload_error
          }
        }
      }
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '重传失败')
  } finally {
    reuploading.value = ''
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

.prompt-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fafbfc;
}

.prompt-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.name-input {
  width: 240px;
}

.index {
  color: #909399;
}

.task-block {
  margin-bottom: 16px;
}

.task-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.err {
  color: var(--el-color-danger);
  font-size: 12px;
}

.img-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.img-cell {
  width: 320px;
}

.img-cell .el-image {
  width: 100%;
  height: 200px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
  background: #fff;
}

.img-ops {
  display: flex;
  gap: 4px;
  align-items: center;
}

.upload-err {
  color: var(--el-color-warning);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
