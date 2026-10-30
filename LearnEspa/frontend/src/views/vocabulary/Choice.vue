<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import StudyProgress from '@/components/StudyProgress.vue'
import { useVocabularyStore } from '@/stores/vocabulary'

defineOptions({ name: 'VocabChoiceView' })

const router = useRouter()
const study = useVocabularyStore()
const session = computed(() => study.state?.session)
const question = computed(() => session.value?.question)
const feedback = computed(() => session.value?.feedback)
const positionText = computed(() => {
  const current = session.value
  if (!current) return ''
  const position = current.done + (feedback.value?.correct ? 0 : 1)
  return `第 ${Math.min(position, current.total)} / ${current.total} 个`
})
const letters = ['A', 'B', 'C', 'D']

onMounted(async () => {
  await study.load()
  if (study.state && study.route !== '/vocabulary/choice') router.replace(study.route)
})

function optionClass(index: number) {
  if (!feedback.value) return {}
  if (index === feedback.value.correctOptionIndex) return { 'is-correct': true }
  if (index === feedback.value.submittedAnswer) return { 'is-wrong': true }
  return {}
}

async function next() {
  await study.next()
  if (study.state && study.route !== '/vocabulary/choice') router.replace(study.route)
}
</script>

<template>
  <div v-if="study.loading" class="card text-dim">正在加载第一课单词…</div>
  <div v-else-if="!study.state" class="card">
    <p>{{ study.error || '暂时无法加载学习进度' }}</p>
    <RouterLink class="btn btn--primary" to="/vocabulary">返回章节页</RouterLink>
  </div>
  <div v-else-if="session?.stage === 'choice' && question" >
    <StudyProgress
      title="第1课 · 看西语选中文"
      :percent="Math.round((session.done / session.total) * 100)"
      :position-text="positionText"
      :meta-text="`本阶段错误：${session.errors} 次`"
    />
    <section class="card word-card">
      <div><span class="word-card__lemma">{{ question.lemma }}</span></div>
      <div v-if="question.pos" class="word-card__pos">{{ question.pos }}</div>
      <div class="options">
        <button
          v-for="(option, index) in question.options"
          :key="`${index}-${option}`"
          type="button"
          class="option"
          :class="optionClass(index)"
          :disabled="Boolean(feedback) || study.busy"
          @click="study.submit(index)"
        >
          <span class="idx">{{ letters[index] }}</span><span>{{ option }}</span>
        </button>
      </div>
      <div v-if="feedback" class="feedback-banner is-show" :class="feedback.correct ? 'feedback-banner--ok' : 'feedback-banner--bad'">
        {{ feedback.correct ? '✓ 正确' : `✗ 正确答案：${feedback.correctAnswer}` }}
      </div>
      <p v-if="study.error" class="text-sub">{{ study.error }}</p>
      <div style="margin-top: 24px">
        <button v-if="feedback" class="btn btn--primary" type="button" :disabled="study.busy" @click="next">
          下一题 →
        </button>
        <button v-else class="btn btn--ghost" type="button" :disabled="study.busy" @click="study.submit(null)">
          暂时不会
        </button>
      </div>
      <p class="text-dim" style="font-size: var(--fs-xs); margin-top: 16px">
        答错的词会等本轮其他单词做完后再次出现，直到答对。
      </p>
    </section>
  </div>
</template>
