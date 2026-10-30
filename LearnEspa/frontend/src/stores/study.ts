import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnalysisStatus, ImitationTask } from '@/types'
import { getCurrentImitationTask } from '@/api'

/** 仿写原型状态；真实背词进度由 vocabulary store 和后端管理。 */
export const useStudyStore = defineStore('study', () => {
  const imitationTask = ref<ImitationTask | null>(null)
  const imitationDraft = ref('')
  const submittedAnswer = ref('')
  const analysisStatus = ref<AnalysisStatus>('pending')
  const analysisStep = ref(0)

  async function loadImitationTask() {
    if (imitationTask.value) return
    imitationTask.value = await getCurrentImitationTask()
  }

  function submitImitationAnswer(text: string) {
    submittedAnswer.value = text
    imitationDraft.value = text
    analysisStatus.value = 'analyzing'
    analysisStep.value = 0
  }

  function tickAnalysis() {
    analysisStep.value = Math.min(analysisStep.value + 1, 4)
    if (analysisStep.value >= 4) analysisStatus.value = 'analyzed'
  }

  function cancelAnalysis() {
    analysisStatus.value = 'pending'
    analysisStep.value = 0
  }

  function resetImitation() {
    imitationDraft.value = ''
    cancelAnalysis()
  }

  return {
    imitationTask, imitationDraft, submittedAnswer, analysisStatus, analysisStep,
    loadImitationTask, submitImitationAnswer, tickAnalysis, cancelAnalysis, resetImitation,
  }
})
