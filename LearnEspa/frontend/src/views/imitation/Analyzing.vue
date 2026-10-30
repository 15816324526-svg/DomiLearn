<script setup lang="ts">
/**
 * 课文仿写 · AI 分析中
 * 真实实现：轮询 GET /api/imitation-sessions/{id}/analyze 直到 analyzed
 * demo 实现：每 700ms 完成一个维度，4 个维度后跳转反馈页
 */
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStudyStore } from '@/stores/study'

defineOptions({ name: 'ImitationAnalyzingView' })

const router = useRouter()
const study = useStudyStore()

const dimensions = ['词汇使用', '句式迁移', '语法表达', '训练目标']

let timer: ReturnType<typeof setInterval> | null = null
let jumpTimer: ReturnType<typeof setTimeout> | null = null

function stopTimers() {
  if (timer) clearInterval(timer)
  if (jumpTimer) clearTimeout(jumpTimer)
  timer = null
  jumpTimer = null
}

function isDone(index: number) {
  return index < study.analysisStep
}

/** 启动轮询：demo 阶段用定时器模拟后端分析进度 */
function startAnalysis() {
  study.cancelAnalysis()
  study.analysisStatus = 'analyzing'

  timer = setInterval(() => {
    study.tickAnalysis()
    if (study.analysisStatus === 'analyzed') {
      stopTimers()
      jumpTimer = setTimeout(() => router.push('/imitation/feedback'), 500)
    }
  }, 700)
}

function onBack() {
  stopTimers()
  study.cancelAnalysis()
  router.push('/imitation') // 草稿仍在 store 里，回到工作台时字还在
}

function onCancel() {
  stopTimers()
  study.cancelAnalysis()
  router.push('/imitation')
}

onMounted(startAnalysis)
onUnmounted(stopTimers)
</script>

<template>
  <section class="card analyzing">
    <div class="spinner" style="width: 28px; height: 28px; margin: 0 auto 18px"></div>
    <h1 style="font-size: 22px; margin-bottom: 10px">正在分析你的仿写</h1>
    <p class="text-sub">系统正在检查词汇使用、句式迁移、语法表达和训练目标。</p>

    <!-- 四个分析维度：顺序点亮，仅作进度提示 -->
    <div class="analyzing__dims" data-field="analysis.dimensions">
      <div v-for="(name, index) in dimensions" :key="name" class="analyzing__dim">
        <span v-if="isDone(index)" style="color: var(--tint-green-text)">✓</span>
        <span v-else class="spinner"></span>
        {{ name }}
      </div>
    </div>

    <div class="analyzing__actions">
      <button class="btn btn--ghost" type="button" @click="onBack">返回修改</button>
      <button class="btn btn--ghost" type="button" @click="onCancel">取消本次分析</button>
    </div>
  </section>
</template>
