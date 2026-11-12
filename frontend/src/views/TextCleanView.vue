<template>
  <div class="page-card">
    <div class="page-head">
      <h3>文本清洗</h3>
      <span class="hint">按分隔符分段 → 段内多余空白归一 → 段间空行拼接（与原脚本行为一致，纯本地处理）</span>
    </div>

    <el-row :gutter="20">
      <el-col :span="12">
        <div class="pane-head">
          <span>输入</span>
          <div class="pane-ops">
            <el-upload :auto-upload="false" :show-file-list="false" accept=".txt" :on-change="loadFile">
              <el-button size="small">导入 .txt</el-button>
            </el-upload>
            <el-button size="small" @click="input = ''">清空</el-button>
          </div>
        </div>
        <el-input v-model="input" type="textarea" :rows="18" placeholder="粘贴待清洗文本…" />
        <div class="sep-row">
          <span>分段分隔符</span>
          <el-input v-model="separator" style="width: 300px" class="mono" />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="pane-head">
          <span>
            输出
            <el-tag size="small" type="info">{{ sectionCount }} 段</el-tag>
            <el-tag size="small" type="info">{{ output.length }} 字符</el-tag>
          </span>
          <div class="pane-ops">
            <el-button size="small" type="primary" @click="copy">复制</el-button>
            <el-button size="small" @click="download">下载 .txt</el-button>
          </div>
        </div>
        <pre class="result-view">{{ output || '（清洗结果将实时显示在这里）' }}</pre>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'

const input = ref('')
const separator = ref('=====从这里截断=====')

// 与 script.py 行为一致：
//   sections = content.split(sep); cleaned = " ".join(s.split()); 过滤空段; "\n\n".join
const output = computed(() => {
  if (!input.value) return ''
  const sep = separator.value || '\n'
  const cleaned = input.value
    .split(sep)
    .map((s) => s.split(/\s+/).filter(Boolean).join(' '))
    .filter(Boolean)
  return cleaned.join('\n\n')
})

const sectionCount = computed(() => (output.value ? output.value.split('\n\n').length : 0))

function loadFile(file: UploadFile) {
  if (!file.raw) return
  const reader = new FileReader()
  reader.onload = () => {
    input.value = String(reader.result ?? '')
  }
  reader.readAsText(file.raw, 'utf-8')
}

async function copy() {
  if (!output.value) return
  await navigator.clipboard.writeText(output.value)
  ElMessage.success('已复制到剪贴板')
}

function download() {
  if (!output.value) return
  const blob = new Blob([output.value], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'cleaned.txt'
  a.click()
  URL.revokeObjectURL(a.href)
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

.pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  min-height: 32px;
}

.pane-ops {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sep-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #606266;
  font-size: 13px;
}

.result-view {
  height: 436px;
}
</style>
