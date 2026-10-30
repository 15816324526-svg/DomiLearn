<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useVocabularyStore } from '@/stores/vocabulary'

defineOptions({ name: 'VocabSummaryView' })

const router = useRouter()
const study = useVocabularyStore()
const summary = computed(() => study.state?.session.summary)

onMounted(async () => {
  await study.load()
  if (study.state && study.route !== '/vocabulary/summary') router.replace(study.route)
})
</script>

<template>
  <div v-if="study.loading" class="card text-dim">正在读取本轮总结…</div>
  <div v-else-if="!study.state" class="card">
    <p>{{ study.error || '暂时无法读取学习总结' }}</p>
    <RouterLink class="btn btn--primary" to="/vocabulary">返回章节页</RouterLink>
  </div>
  <div v-else-if="summary" style="max-width: 880px">
    <section class="card" style="text-align: center; padding: 40px 32px 32px">
      <span class="badge badge--green" style="margin-bottom: 14px">✓ 已完成</span>
      <h1 style="font-size: 26px; margin-bottom: 10px">第一课单词学习完成</h1>
      <p class="text-sub">两个阶段均已完成。错过的单词已保存在复习池，供后续仿写训练使用。</p>
      <div class="stat-row" style="margin-top: 28px; margin-bottom: 0">
        <div class="stat"><div class="k">学习单词</div><div class="v">{{ summary.learned }} 个</div></div>
        <div class="stat"><div class="k">需要复习</div><div class="v">{{ summary.review }} 个</div></div>
        <div class="stat"><div class="k">答题次数</div><div class="v">{{ summary.attempts }} 次</div></div>
      </div>
    </section>

    <div class="result-grid">
      <section class="card">
        <div class="card__head"><h2 class="card__title">复习池</h2><span class="badge badge--yellow">{{ summary.reviewWords.length }} 词</span></div>
        <div v-if="summary.reviewWords.length" class="result-list">
          <div v-for="word in summary.reviewWords" :key="word.id" class="result-item">
            <div><div class="lemma">{{ word.lemma }}</div><div class="why">{{ word.meaning }} · {{ word.reason }}</div></div>
            <span class="badge">复习池</span>
          </div>
        </div>
        <p v-else class="text-sub">这一轮没有答错的单词。</p>
      </section>
      <section class="card">
        <div class="card__head"><h2 class="card__title">本轮表现稳定</h2><span class="badge badge--green">{{ summary.stableWords.length }} 词</span></div>
        <div class="result-list">
          <div v-for="word in summary.stableWords" :key="word.id" class="result-item">
            <span class="lemma">{{ word.lemma }}</span><span class="why">{{ word.meaning }}</span>
          </div>
        </div>
      </section>
    </div>
    <div class="result-actions"><RouterLink class="btn btn--primary" to="/vocabulary">返回章节</RouterLink></div>
  </div>
</template>
