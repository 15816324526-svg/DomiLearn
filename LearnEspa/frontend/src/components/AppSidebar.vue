<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { NavKey, SidebarTask } from '@/types'
import { mockSidebarTasks, mockVocabPending } from '@/mock'

/** 侧栏导航项：to 为空表示功能未开放（渲染成不可点的占位） */
interface NavItem {
  key: NavKey
  label: string
  to?: string
  count?: number
}

const navItems: NavItem[] = [
  { key: 'home', label: '仪表盘', to: '/' },
  { key: 'textbook', label: '教材目录', to: '/textbook' },
  { key: 'vocabulary', label: '词汇复习', to: '/vocabulary', count: mockVocabPending },
  { key: 'imitation', label: '仿写练习', to: '/imitation' },
  { key: 'report', label: '学习报告', to: '/imitation/report' },
]

const route = useRoute()

/** 当前激活模块：来自路由 meta.nav（见 router/index.ts） */
const activeNav = computed<NavKey>(() => (route.meta.nav as NavKey) ?? 'home')

const isActive = (item: NavItem) => item.key === activeNav.value

/** 任务圆点颜色映射——只使用 theme.css 里的低饱和色 */
const dotColor = (tone: SidebarTask['tone']) =>
  `var(--tint-${tone}-dot)` as string

const stateColor = (tone: SidebarTask['tone']) =>
  `var(--tint-${tone}-text)` as string
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__label">学习空间</div>

    <nav class="sidebar__nav">
      <!-- 已开放：可点击跳转 -->
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to ?? ''"
        class="sidebar__link"
        :class="{ 'is-active': isActive(item) }"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        {{ item.label }}
        <span v-if="item.count" class="sidebar__count">{{ item.count }}</span>
      </RouterLink>

    </nav>

    <div class="sidebar__section">
      <div class="sidebar__label">今日任务清单</div>
      <div v-for="task in mockSidebarTasks" :key="task.name" class="sidebar__task">
        <span class="dot" :style="{ background: dotColor(task.tone) }"></span>
        {{ task.name }} <span class="num">({{ task.done }}/{{ task.total }})</span>
        <span class="state" :style="{ color: stateColor(task.tone) }">{{ task.stateText }}</span>
      </div>
    </div>

    <div class="sidebar__footer">
      <span>现代西班牙语 1 (册)</span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </div>
  </aside>
</template>
