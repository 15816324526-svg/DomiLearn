import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getVocabularyStudy, nextVocabularyQuestion, submitVocabularyAnswer } from '@/api'
import type { VocabularyStudyState } from '@/types'

export const useVocabularyStore = defineStore('vocabulary', () => {
  const state = ref<VocabularyStudyState | null>(null)
  const loading = ref(false)
  const busy = ref(false)
  const error = ref('')
  const storedLesson = Number(sessionStorage.getItem('domilearn.vocabulary.lesson'))
  const lessonNumber = ref(Number.isInteger(storedLesson) && storedLesson >= 1 && storedLesson <= 16 ? storedLesson : 1)

  const route = computed(() => {
    switch (state.value?.session.stage) {
      case 'choice': return '/vocabulary/choice'
      case 'dictation': return '/vocabulary/dictation'
      case 'complete': return '/vocabulary/summary'
      default: return '/vocabulary'
    }
  })

  async function load(number = lessonNumber.value) {
    lessonNumber.value = number
    sessionStorage.setItem('domilearn.vocabulary.lesson', String(number))
    loading.value = true
    error.value = ''
    try {
      state.value = await getVocabularyStudy(lessonNumber.value)
    } catch (cause) {
      state.value = null
      error.value = cause instanceof Error ? cause.message : '无法加载单词学习进度'
    } finally {
      loading.value = false
    }
  }

  async function submit(answer: string | number | null) {
    const session = state.value?.session
    if (!session?.question || session.feedback || busy.value) return
    busy.value = true
    error.value = ''
    try {
      state.value = await submitVocabularyAnswer(session.id, session.question.id, answer, crypto.randomUUID(), lessonNumber.value)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '答案未能保存，请重试'
      // 请求可能已在后端保存；重新读取可避免下一次点击重复计分。
      await load()
    } finally {
      busy.value = false
    }
  }

  async function next() {
    const session = state.value?.session
    if (!session?.feedback || busy.value) return
    busy.value = true
    error.value = ''
    try {
      state.value = await nextVocabularyQuestion(session.id, lessonNumber.value)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '无法进入下一题'
      await load()
    } finally {
      busy.value = false
    }
  }

  return { state, loading, busy, error, lessonNumber, route, load, submit, next }
})
