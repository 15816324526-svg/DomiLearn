/** 全局轻提示（页面底部的黑色胶囊） */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const message = ref('')
  const visible = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  function showToast(text: string, duration = 1800) {
    message.value = text
    visible.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      visible.value = false
    }, duration)
  }

  return { message, visible, showToast }
})
