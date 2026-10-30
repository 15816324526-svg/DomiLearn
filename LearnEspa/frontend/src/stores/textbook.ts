import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  confirmTextbookImport,
  getTextbookState,
  retryTextbookImport,
  uploadTextbook,
} from '@/api'
import type { TextbookState } from '@/types'

const ACTIVE = new Set(['queued', 'processing'])

export const useTextbookStore = defineStore('textbook', () => {
  const state = ref<TextbookState | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const connectionError = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  const latestJob = computed(() => state.value?.latestJob ?? null)
  const isActive = computed(() => Boolean(latestJob.value && ACTIVE.has(latestJob.value.status)))

  async function load(silent = false) {
    if (!silent) loading.value = true
    try {
      state.value = await getTextbookState()
      connectionError.value = ''
    } catch (error) {
      connectionError.value = error instanceof Error ? error.message : '无法连接后端'
      throw error
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function upload(file: File) {
    uploading.value = true
    try {
      await uploadTextbook(file)
      await load(true)
      schedulePoll()
    } finally {
      uploading.value = false
    }
  }

  async function confirm() {
    if (!latestJob.value) return
    state.value = await confirmTextbookImport(latestJob.value.id)
    stopPolling()
  }

  async function retry() {
    if (!latestJob.value) return
    await retryTextbookImport(latestJob.value.id)
    await load(true)
    schedulePoll()
  }

  function schedulePoll() {
    stopPolling()
    if (!isActive.value) return
    const delay = document.hidden ? 12000 : 3000
    timer = setTimeout(async () => {
      try {
        await load(true)
      } catch {
        // 保留最后一次可靠状态，下一轮继续尝试。
      }
      schedulePoll()
    }, delay)
  }

  function startPolling() {
    schedulePoll()
  }

  function stopPolling() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  return {
    state,
    latestJob,
    loading,
    uploading,
    connectionError,
    isActive,
    load,
    upload,
    confirm,
    retry,
    startPolling,
    stopPolling,
  }
})
