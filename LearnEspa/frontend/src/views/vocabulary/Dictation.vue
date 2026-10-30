<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StudyProgress from '@/components/StudyProgress.vue'
import AccentKeypad from '@/components/AccentKeypad.vue'
import { useVocabularyStore } from '@/stores/vocabulary'
import { insertAt } from '@/utils/text'

defineOptions({ name: 'VocabDictationView' })

const router = useRouter()
const study = useVocabularyStore()
const answer = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const session = computed(() => study.state?.session)
const question = computed(() => session.value?.question)
const feedback = computed(() => session.value?.feedback)
const positionText = computed(() => {
  const current = session.value
  if (!current) return ''
  const position = current.done + (feedback.value?.correct ? 0 : 1)
  return `第 ${Math.min(position, current.total)} / ${current.total} 个`
})

onMounted(async () => {
  await study.load()
  if (study.state && study.route !== '/vocabulary/dictation') {
    router.replace(study.route)
    return
  }
  answer.value = typeof feedback.value?.submittedAnswer === 'string' ? feedback.value.submittedAnswer : ''
  if (!feedback.value) nextTick(() => inputRef.value?.focus())
})

async function submit() {
  if (!answer.value.trim() || feedback.value || study.busy) return
  await study.submit(answer.value)
}

async function next() {
  await study.next()
  answer.value = ''
  if (study.state && study.route !== '/vocabulary/dictation') router.replace(study.route)
  else nextTick(() => inputRef.value?.focus())
}

function onInsert(char: string) {
  if (feedback.value) return
  const input = inputRef.value
  if (!input) return
  const start = input.selectionStart ?? answer.value.length
  const end = input.selectionEnd ?? start
  answer.value = insertAt(answer.value, char, start, end)
  nextTick(() => {
    input.focus()
    input.setSelectionRange(start + char.length, start + char.length)
  })
}
</script>

<template>
  <div v-if="study.loading" class="card text-dim">正在加载拼写任务…</div>
  <div v-else-if="!study.state" class="card">
    <p>{{ study.error || '暂时无法加载学习进度' }}</p>
    <RouterLink class="btn btn--primary" to="/vocabulary">返回章节页</RouterLink>
  </div>
  <div v-else-if="session?.stage === 'dictation' && question">
    <StudyProgress
      title="第1课 · 看中文拼西语"
      :percent="Math.round((session.done / session.total) * 100)"
      :position-text="positionText"
      :meta-text="`本阶段错误：${session.errors} 次`"
    />
    <section class="card dictation-card">
      <p class="text-dim" style="font-size: var(--fs-sm); margin-bottom: 10px">请写出对应的西语单词</p>
      <div class="dictation-card__meaning">{{ question.meaning }}</div>
      <p v-if="question.hint" class="text-sub">提示：{{ question.hint }}</p>
      <input
        ref="inputRef" v-model="answer" class="field" type="text"
        placeholder="输入西语单词，Enter 提交" autocomplete="off" spellcheck="false"
        :disabled="Boolean(feedback) || study.busy" @keydown.enter="submit"
      />
      <AccentKeypad v-if="!feedback" @insert="onInsert" />
      <div v-if="feedback" class="feedback-banner is-show" :class="feedback.correct ? 'feedback-banner--ok' : 'feedback-banner--bad'">
        {{ feedback.correct ? `✓ 正确，教材写法：${feedback.correctAnswer}` : `✗ 正确答案：${feedback.correctAnswer}` }}
      </div>
      <p v-if="study.error" class="text-sub">{{ study.error }}</p>
      <div class="dictation-actions">
        <button v-if="feedback" class="btn btn--primary" type="button" :disabled="study.busy" @click="next">下一题 →</button>
        <template v-else>
          <button class="btn btn--ghost" type="button" :disabled="study.busy" @click="study.submit(null)">暂时不会</button>
          <button class="btn btn--primary" type="button" :disabled="study.busy || !answer.trim()" @click="submit">提交答案</button>
        </template>
      </div>
    </section>
  </div>
</template>
