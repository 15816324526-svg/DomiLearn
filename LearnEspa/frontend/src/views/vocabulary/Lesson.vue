<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVocabularyStore } from '@/stores/vocabulary'
import { getVocabularyLessons } from '@/api'

defineOptions({ name: 'VocabLessonView' })

const router = useRouter()
const route = useRoute()
const study = useVocabularyStore()
const lessons = ref<Array<{ number: number; title: string }>>([])

onMounted(async () => {
  const selected = Number(route.query.lesson)
  await study.load(Number.isInteger(selected) && selected >= 1 && selected <= 16 ? selected : study.lessonNumber)
  try { lessons.value = await getVocabularyLessons() } catch { /* 学习入口仍可显示当前章节 */ }
})

async function selectLesson(number: number) {
  await router.replace({ path: '/vocabulary', query: { lesson: String(number) } })
  await study.load(number)
}

function continueStudy() {
  router.push(study.route)
}
</script>

<template>
  <div v-if="study.loading" class="card text-dim">正在读取第 {{ study.lessonNumber }} 课词表…</div>
  <div v-else-if="study.error" class="card">
    <h1>暂时无法开始背词</h1>
    <p class="text-sub">{{ study.error }}</p>
    <RouterLink class="btn btn--primary" to="/textbook">前往教材目录</RouterLink>
  </div>
  <div v-else-if="study.state" class="card lesson-hero">
    <div class="crumbs"><RouterLink to="/">现代西班牙语1</RouterLink> / 第{{ study.lessonNumber }}课</div>
    <h1 class="lesson-hero__title">{{ study.state.overview.title }}</h1>
    <p class="lesson-hero__desc">{{ study.state.overview.description }}</p>
    <div class="stat-row">
      <div class="stat"><div class="k">单词数量</div><div class="v">{{ study.state.overview.wordCount }} 个</div></div>
      <div class="stat"><div class="k">学习流程</div><div class="v">释义选择 → 中文拼写</div></div>
      <div class="stat"><div class="k">当前进度</div><div class="v">{{ study.state.session.stage === 'complete' ? '已完成' : `${study.state.session.done} / ${study.state.session.total}` }}</div></div>
    </div>
    <button class="btn btn--primary btn--lg" type="button" @click="continueStudy">
      {{ study.state.session.stage === 'complete' ? '查看本轮总结' : study.state.session.done || study.state.session.stage === 'dictation' ? '继续学习' : '开始本章单词学习' }} →
    </button>
    <p class="text-dim" style="font-size: var(--fs-sm); margin-top: 14px; text-align: center">
      每题作答后自动保存，随时可以暂停。
    </p>
    <div v-if="lessons.length > 1" style="margin-top: 24px">
      <h2 style="font-size: var(--fs-lg); margin-bottom: 12px">选择其他章节</h2>
      <div style="display: flex; flex-wrap: wrap; gap: 8px">
        <button v-for="lesson in lessons" :key="lesson.number" type="button" class="btn btn--ghost"
          :disabled="study.loading || lesson.number === study.lessonNumber" @click="selectLesson(lesson.number)">
          第{{ lesson.number }}课
        </button>
      </div>
    </div>
  </div>
</template>
