<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTextbookStore } from '@/stores/textbook'
import { useUiStore } from '@/stores/ui'

const MAX_BYTES = 500 * 1024 * 1024
const store = useTextbookStore()
const ui = useUiStore()
const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

const job = computed(() => store.latestJob)
const current = computed(() => store.state?.currentVersion ?? null)
const view = computed(() => {
  if (store.loading && !store.state) return 'loading'
  if (store.uploading) return 'uploading'
  if (job.value?.status === 'queued' || job.value?.status === 'processing') return 'processing'
  if (job.value?.status === 'awaiting_confirmation') return 'success'
  if (job.value?.status === 'failed') return 'failed'
  if (current.value) return 'confirmed'
  return 'empty'
})

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return minutes ? `${minutes} 分 ${rest} 秒` : `${rest} 秒`
}

function openPicker() {
  fileInput.value?.click()
}

async function selectFile(file?: File) {
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    ui.showToast('请选择 PDF 文件')
    return
  }
  if (file.size > MAX_BYTES) {
    ui.showToast('PDF 文件不能超过 500 MB')
    return
  }
  try {
    await store.upload(file)
    ui.showToast('教材已上传，正在解析')
  } catch (error) {
    ui.showToast(error instanceof Error ? error.message : '上传失败，请重试')
  }
}

function onInput(event: Event) {
  const input = event.target as HTMLInputElement
  void selectFile(input.files?.[0])
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  void selectFile(event.dataTransfer?.files[0])
}

async function confirmResult() {
  try {
    await store.confirm()
    ui.showToast('教材版本已确认')
  } catch (error) {
    ui.showToast(error instanceof Error ? error.message : '确认失败')
  }
}

async function retry() {
  try {
    await store.retry()
    ui.showToast('已重新开始解析')
  } catch (error) {
    ui.showToast(error instanceof Error ? error.message : '重新解析失败')
  }
}

onMounted(async () => {
  try {
    await store.load()
    store.startPolling()
  } catch {
    ui.showToast('无法连接后端，请确认后端已经启动')
  }
})

onUnmounted(() => store.stopPolling())
</script>

<template>
  <section class="textbook-page">
    <header class="textbook-head">
      <div>
        <div class="crumbs">教材管理</div>
        <h1>教材目录</h1>
        <p class="text-sub">导入《现代西班牙语1》PDF，并确认技术解析结果。</p>
      </div>
      <span v-if="current" class="badge badge--green">已启用</span>
    </header>

    <p v-if="store.connectionError" class="textbook-connection">{{ store.connectionError }}</p>

    <section v-if="view === 'loading'" class="card textbook-status textbook-status--center">
      <span class="spinner"></span><span>正在读取教材状态…</span>
    </section>

    <section v-else-if="view === 'empty'" class="card textbook-upload-card">
      <input ref="fileInput" class="textbook-file-input" type="file" accept="application/pdf,.pdf" @change="onInput">
      <button
        type="button"
        class="textbook-dropzone"
        :class="{ 'is-dragging': dragging }"
        @click="openPicker"
        @dragenter.prevent="dragging = true"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
      >
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
          <path d="M12 16V4m0 0L7 9m5-5 5 5" />
          <path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" />
        </svg>
        <strong>将教材 PDF 拖到这里</strong>
        <span>或点击选择文件</span>
        <small>仅支持 PDF，最大 500 MB</small>
      </button>
    </section>

    <section v-else-if="view === 'uploading'" class="card textbook-status textbook-status--center">
      <span class="spinner"></span>
      <div><strong>正在上传教材</strong><p class="text-dim">大文件需要一点时间，请勿关闭后端。</p></div>
    </section>

    <section v-else-if="view === 'processing'" class="card textbook-status">
      <div class="textbook-status__title">
        <span class="spinner"></span>
        <div><h2>正在解析教材</h2><p class="text-dim">{{ job?.displayFilename }}</p></div>
        <span class="badge badge--yellow">{{ job?.status === 'queued' ? '等待中' : '解析中' }}</span>
      </div>
      <dl class="textbook-meta">
        <div><dt>教材</dt><dd>现代西班牙语1</dd></div>
        <div><dt>总页数</dt><dd>{{ job?.totalPages }} 页</dd></div>
        <div><dt>已运行</dt><dd>{{ formatElapsed(job?.elapsedSeconds ?? 0) }}</dd></div>
        <div v-if="job?.processedPages !== null"><dt>真实进度</dt><dd>{{ job?.processedPages }} / {{ job?.totalPages }} 页</dd></div>
      </dl>
      <p class="textbook-note">整本教材通常需要 20～40 分钟。你可以离开此页面，后端会继续解析。</p>
      <p v-if="current" class="textbook-current-note">当前已确认版本仍在正常使用：{{ current.displayFilename }}</p>
    </section>

    <section v-else-if="view === 'success'" class="card textbook-status">
      <div class="textbook-result textbook-result--success"><strong>教材解析成功</strong><span>程序已生成转换结果，内容可能存在少量识别误差。</span></div>
      <dl class="textbook-meta">
        <div><dt>文件</dt><dd>{{ job?.displayFilename }}</dd></div>
        <div><dt>页数</dt><dd>{{ job?.totalPages }} 页</dd></div>
        <div><dt>结果</dt><dd>Markdown + JSON</dd></div>
      </dl>
      <div class="textbook-actions">
        <button class="btn btn--primary" type="button" @click="confirmResult">确认使用</button>
        <button class="btn btn--ghost" type="button" @click="retry">重新解析</button>
      </div>
      <p v-if="current" class="textbook-current-note">确认前仍在使用：{{ current.displayFilename }}</p>
    </section>

    <section v-else-if="view === 'failed'" class="card textbook-status">
      <div class="textbook-result textbook-result--failed"><strong>教材解析失败</strong><span>{{ job?.errorMessage || '解析过程未完成，请重新尝试。' }}</span></div>
      <dl class="textbook-meta">
        <div><dt>文件</dt><dd>{{ job?.displayFilename }}</dd></div>
        <div><dt>失败原因</dt><dd>{{ job?.errorCode || 'CONVERSION_FAILED' }}</dd></div>
      </dl>
      <div class="textbook-actions">
        <button class="btn btn--primary" type="button" @click="retry">重新解析</button>
        <button class="btn btn--ghost" type="button" @click="openPicker">更换文件</button>
        <input ref="fileInput" class="textbook-file-input" type="file" accept="application/pdf,.pdf" @change="onInput">
      </div>
      <p v-if="current" class="textbook-current-note">解析失败不影响当前版本：{{ current.displayFilename }}</p>
    </section>

    <section v-else class="card textbook-status">
      <div class="textbook-status__title">
        <div><h2>现代西班牙语1</h2><p class="text-dim">{{ current?.displayFilename }}</p></div>
        <span class="badge badge--green">已启用</span>
      </div>
      <dl class="textbook-meta">
        <div><dt>页数</dt><dd>{{ current?.pageCount }} 页</dd></div>
        <div><dt>确认时间</dt><dd>{{ current ? new Date(current.confirmedAt).toLocaleString('zh-CN') : '' }}</dd></div>
      </dl>
      <div class="textbook-actions"><button class="btn btn--ghost" type="button" @click="retry">重新解析</button></div>
    </section>
  </section>
</template>
