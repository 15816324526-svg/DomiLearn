import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { nav: 'home' }, // 与 types.ts 的 NavKey 对应，侧栏高亮用
  },
  {
    path: '/textbook',
    name: 'textbook-directory',
    component: () => import('@/views/textbook/Directory.vue'),
    meta: { nav: 'textbook' },
  },

  /* ---------- 背单词：任务页 → 释义选择 → 中文默写 → 本轮总结 ---------- */
  {
    path: '/vocabulary',
    name: 'vocab-lesson',
    component: () => import('@/views/vocabulary/Lesson.vue'),
    meta: { nav: 'vocabulary' },
  },
  {
    path: '/vocabulary/choice',
    name: 'vocab-choice',
    component: () => import('@/views/vocabulary/Choice.vue'),
    meta: { nav: 'vocabulary' },
  },
  {
    path: '/vocabulary/dictation',
    name: 'vocab-dictation',
    component: () => import('@/views/vocabulary/Dictation.vue'),
    meta: { nav: 'vocabulary' },
  },
  {
    path: '/vocabulary/summary',
    name: 'vocab-summary',
    component: () => import('@/views/vocabulary/Summary.vue'),
    meta: { nav: 'vocabulary' },
  },

  /* ---------- 课文仿写：同一工作台逐句提交、反馈与推进 ---------- */
  {
    path: '/imitation',
    name: 'imitation',
    component: () => import('@/views/imitation/Workspace.vue'),
    meta: { nav: 'imitation' },
  },
  {
    path: '/imitation/analyzing',
    redirect: '/imitation',
  },
  {
    path: '/imitation/feedback',
    redirect: '/imitation',
  },
  {
    path: '/imitation/report',
    name: 'report',
    component: () => import('@/views/imitation/Report.vue'),
    meta: { nav: 'report' },
  },
]

/* 未知路径兜底回到首页（真实项目里应换成 404 页） */
routes.push({ path: '/:pathMatch(.*)*', redirect: '/' })

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
