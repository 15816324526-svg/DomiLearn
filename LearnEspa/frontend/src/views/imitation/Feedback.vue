<script setup lang="ts">
/**
 * 课文仿写 · 反馈
 * API: GET /api/imitation-evaluations/{evaluationId}
 * 语义 / 语法 / 训练目标分开判断，不合并总分（产品规则，见 PRD）
 */
import { computed, onMounted, ref } from 'vue'
import type { ImitationEvaluation, VerdictLevel } from '@/types'
import { getEvaluation } from '@/api'
import { useStudyStore } from '@/stores/study'

defineOptions({ name: 'ImitationFeedbackView' })

const study = useStudyStore()
const evaluation = ref<ImitationEvaluation | null>(null)

onMounted(async () => {
  evaluation.value = await getEvaluation()
})

/** 三档结论文案与颜色：颜色只允许从 theme 里取低饱和色 */
const levelStyle: Record<VerdictLevel, { text: string; color: string }> = {
  pass: { text: '通过', color: 'var(--tint-green-text)' },
  weak: { text: '需要加强', color: 'var(--tint-yellow-text)' },
  missed: { text: '未完成', color: 'var(--tint-red-text)' },
}

/** 用户在 store 里提交的真实答案优先于 mock 答案 */
const userAnswer = computed(() => study.submittedAnswer || evaluation.value?.attempt.userAnswer || '')
</script>

<template>
  <div v-if="evaluation" style="max-width: 980px">
    <!-- 你的表达 -->
    <section class="card" style="margin-bottom: 20px">
      <div class="card__head">
        <h2 class="card__title">你的表达</h2>
        <span class="badge" data-field="attempt.submittedAt">
          第 {{ evaluation.attempt.position }} 句 · {{ evaluation.attempt.submittedAt }} 提交
        </span>
      </div>
      <p style="font-size: var(--fs-lg); line-height: 1.9" data-field="attempt.userAnswer">
        {{ userAnswer }}
      </p>
    </section>

    <!-- 三个核心结论：分开判断，不合并总分 -->
    <div class="verdicts" data-field="evaluation.verdicts">
      <div v-for="item in evaluation.verdicts" :key="item.key" class="card verdict">
        <div class="k">{{ item.label }}</div>
        <div class="v" :style="{ color: levelStyle[item.level].color }">
          {{ levelStyle[item.level].text }}
        </div>
      </div>
    </div>

    <div class="result-grid" style="grid-template-columns: 1fr 1.4fr">
      <!-- 表达正确 -->
      <section class="card">
        <div class="card__head">
          <h2 class="card__title">表达正确</h2>
          <span class="badge badge--green">{{ evaluation.correct.length }} 处</span>
        </div>
        <div v-for="item in evaluation.correct" :key="item.sentence" class="fb-item">
          <div class="fb-item__line"><span class="yes">{{ item.sentence }}</span></div>
          <p class="fb-item__exp">{{ item.comment }}</p>
        </div>
      </section>

      <!-- 需要加强 -->
      <section class="card">
        <div class="card__head">
          <h2 class="card__title">需要加强</h2>
          <span class="badge badge--yellow">
            {{ evaluation.improve.length }} 处 · 已加入复习池
          </span>
        </div>
        <div v-for="item in evaluation.improve" :key="item.user" class="fb-item">
          <div class="fb-item__line">
            <span class="no">{{ item.user }}</span>&nbsp;&nbsp;→&nbsp;&nbsp;
            <span class="yes">{{ item.expected }}</span>
          </div>
          <p class="fb-item__exp">{{ item.explanation }}</p>
        </div>
      </section>
    </div>

    <!-- 训练目标未完成 -->
    <section class="card" style="margin-top: 20px">
      <div class="card__head">
        <h2 class="card__title">训练目标未完成</h2>
        <span class="badge badge--red">{{ evaluation.targetMissed }} 个 · 已加入复习池</span>
      </div>
      <p class="fb-item__exp" data-field="evaluation.targetMissed">
        {{ evaluation.targetMissedNote }}
        <br />参考表达：{{ evaluation.reference }}
      </p>
    </section>

    <!-- 底部操作 -->
    <div class="result-actions" style="max-width: none">
      <RouterLink class="btn btn--primary" to="/imitation/report">查看本次学习报告 →</RouterLink>
      <RouterLink class="btn btn--ghost" to="/imitation">返回修改</RouterLink>
      <RouterLink class="btn btn--ghost" to="/">返回章节</RouterLink>
    </div>
  </div>

  <div v-else class="card text-dim">正在获取分析结果…</div>
</template>
