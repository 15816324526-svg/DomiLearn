<script setup lang="ts">
/**
 * 学习页顶部进度条
 * ------------------------------------------------------------
 * 默写页、释义页结构一致（标题 + 进度 + 位置/错误数），抽出来复用。
 */
defineOptions({ name: 'StudyProgress' })

defineProps<{
  /** 左侧标题，如 "第1课 · 单词释义选择" */
  title: string
  /** 0-100 */
  percent: number
  /** 位置文案，如 "第 8 / 40 个" */
  positionText: string
  /** 右侧补充信息，如 "本轮错误：2 个"，不传则不显示 */
  metaText?: string
}>()
</script>

<template>
  <div class="study-top">
    <span class="study-top__info"><b>{{ title }}</b></span>

    <div class="progress study-top__bar">
      <div class="progress__track">
        <div class="progress__fill" :style="{ width: percent + '%' }"></div>
      </div>
      <span class="progress__meta">{{ positionText }}</span>
    </div>

    <span v-if="metaText" class="study-top__info">{{ metaText }}</span>
  </div>
</template>
