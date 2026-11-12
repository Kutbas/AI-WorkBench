<template>
  <div class="page-card">
    <div class="page-head">
      <h3>文档解析（SoMark）</h3>
      <span class="hint">PDF / 图片 → Markdown · 纯文本 · 结构化 JSON，支持多文件按序合并</span>
    </div>

    <el-row :gutter="20">
      <el-col :span="14">
        <el-upload
          drag
          multiple
          :auto-upload="false"
          :file-list="fileList"
          :on-change="onFileChange"
          :on-remove="onFileChange"
          :accept="accept"
          class="uploader"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 pdf / png / jpg / bmp / tiff / webp，可多选，按选择顺序解析与合并</div>
          </template>
        </el-upload>
        <div class="opts">
          <el-checkbox v-model="stripRefs">去掉 References 起至文末的内容</el-checkbox>
          <el-checkbox v-model="plain">精简模式（图片只留描述不带链接、Markdown 无页码注释）</el-checkbox>
        </div>
        <el-button type="primary" size="large" :loading="submitting" :disabled="!fileList.length" @click="submit">
          开始解析（{{ fileList.length }} 个文件）
        </el-button>
      </el-col>
      <el-col :span="10">
        <div v-if="job" class="job-panel">
          <div class="job-head">
            <b>{{ job.id }}</b>
            <el-tag :type="statusTag(job.status)" size="small">{{ job.status }}</el-tag>
          </div>
          <el-table :data="job.tasks" size="small">
            <el-table-column label="文件" min-width="160">
              <template #default="{ row }">{{ row.stem ?? row.name }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="块统计" min-width="140">
              <template #default="{ row }">
                <span class="mono">{{ fmtStats(row.stats) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="mergedReady" style="margin-top: 10px">
            <el-button type="success" plain size="small" @click="download(`/api/somark/jobs/${job.id}/merged`)">
              下载合并 all.md
            </el-button>
          </div>
          <el-collapse style="margin-top: 10px">
            <el-collapse-item v-for="t in doneTasks" :key="t.stem" :title="t.stem">
              <div class="file-ops">
                <el-button size="small" @click="preview(t.stem, 'md')">预览 Markdown</el-button>
                <el-button size="small" @click="preview(t.stem, 'txt')">预览纯文本</el-button>
                <el-button size="small" @click="download(`/api/somark/jobs/${job.id}/files/${t.stem}/md`)">
                  下载 .md
                </el-button>
                <el-button size="small" @click="download(`/api/somark/jobs/${job.id}/files/${t.stem}/txt`)">
                  下载 .txt
                </el-button>
                <el-button size="small" @click="download(`/api/somark/jobs/${job.id}/files/${t.stem}/json`)">
                  下载 raw.json
                </el-button>
              </div>
              <div v-if="t.error" class="err">{{ t.error }}</div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-else class="empty-hint">提交解析后，结果会显示在这里</div>
      </el-col>
    </el-row>

    <el-divider content-position="left">历史任务</el-divider>
    <el-table :data="history" size="small" @row-click="loadJob">
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column prop="id" label="任务 ID" width="240" class-name="mono" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="文件">
        <template #default="{ row }">
          {{ (row.params.files as string[] | undefined)?.join('、') ?? row.tasks.length + ' 个文件' }}
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="previewVisible" :title="`预览：${previewTitle}`" width="70%" top="5vh">
      <pre class="result-view mono">{{ previewContent }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadFiles } from 'element-plus'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api, getToken, type Job, type SoMarkTask } from '../api'

const accept = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'].join(',')
const fileList = ref<UploadFile[]>([])
const stripRefs = ref(false)
const plain = ref(false)
const submitting = ref(false)
const job = ref<Job | null>(null)
const history = ref<Job[]>([])
const previewVisible = ref(false)
const previewTitle = ref('')
const previewContent = ref('')
let timer: number | undefined

const doneTasks = computed(() => job.value?.tasks.filter((t) => t.status === 'done' && t.stem) ?? [])
const mergedReady = computed(
  () => job.value !== null && job.value.status !== 'running' && doneTasks.value.length > 1,
)

function statusTag(s: string): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  if (s === 'done') return 'success'
  if (s === 'running') return 'primary'
  if (s === 'pending') return 'info'
  if (s === 'interrupted') return 'warning'
  return 'danger'
}

function fmtStats(stats?: Record<string, number>): string {
  if (!stats) return '—'
  return Object.entries(stats)
    .map(([k, v]) => `${k}:${v}`)
    .join(' ')
}

function onFileChange(_file: UploadFile, files: UploadFiles) {
  fileList.value = [...files]
}

onMounted(refreshHistory)
onBeforeUnmount(stopPolling)

async function refreshHistory() {
  try {
    history.value = await api.get<Job[]>('/api/somark/jobs')
  } catch {
    /* 忽略 */
  }
}

async function submit() {
  if (!fileList.value.length) return
  submitting.value = true
  try {
    const form = new FormData()
    let hasValid = false
    for (const f of fileList.value) {
      if (!f.raw) continue
      form.append('files', f.raw, f.name)
      hasValid = true
    }
    if (!hasValid) {
      ElMessage.warning('未选择有效文件')
      return
    }
    form.append('strip_refs', String(stripRefs.value))
    form.append('plain', String(plain.value))
    const res = await api.postForm<{ job_id: string }>('/api/somark/jobs', form)
    job.value = await api.get<Job>(`/api/somark/jobs/${res.job_id}`)
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
      const j = await api.get<Job>(`/api/somark/jobs/${id}`)
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
    job.value = await api.get<Job>(`/api/somark/jobs/${row.id}`)
    if (job.value.status === 'running') startPolling(row.id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  }
}

async function preview(stem: string | undefined, fmt: 'md' | 'txt') {
  if (!stem || !job.value) return
  previewTitle.value = `${stem}.${fmt}`
  previewContent.value = '加载中…'
  previewVisible.value = true
  const resp = await fetch(`/api/somark/jobs/${job.value?.id}/files/${stem}/${fmt}`, {
    headers: { 'X-Auth-Token': getToken() },
  })
  previewContent.value = resp.ok ? await resp.text() : `加载失败：HTTP ${resp.status}`
}

async function download(path: string) {
  // fetch 带 token 头取回 blob 再触发下载（避免把口令拼进 URL）
  const resp = await fetch(path, { headers: { 'X-Auth-Token': getToken() } })
  if (!resp.ok) {
    ElMessage.error(`下载失败：HTTP ${resp.status}`)
    return
  }
  const disposition = resp.headers.get('content-disposition') ?? ''
  const m = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(disposition)
  const name = m ? decodeURIComponent(m[1]) : path.split('/').pop() ?? 'download'
  const url = URL.createObjectURL(await resp.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.page-head h3 {
  margin: 0;
}

.hint {
  color: #909399;
  font-size: 12px;
}

.uploader :deep(.el-upload-dragger) {
  padding: 28px 16px;
}

.opts {
  margin: 12px 0 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-panel {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  background: #fafbfc;
}

.job-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  justify-content: space-between;
}

.file-ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
}

.err {
  color: var(--el-color-danger);
  font-size: 12px;
  margin-top: 4px;
}

.empty-hint {
  color: #c0c4cc;
  text-align: center;
  padding: 60px 0;
}
</style>
