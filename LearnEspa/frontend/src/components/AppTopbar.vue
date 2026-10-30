<script setup lang="ts">
/* 顶栏：品牌 + 状态徽章 + 通知 + 头像
   右侧头像/通知目前是静态占位，等后端补用户信息后再接 store */
</script>

<template>
  <header class="topbar">
    <div class="topbar__brand">
      <span class="topbar__logo">DomiLearn</span>
      <span class="topbar__slogan">Aquí se aprende.</span>
    </div>

    <div class="topbar__actions">
      <span class="badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2Z" />
          <path d="M4 19a2 2 0 0 0 2 2h13" />
        </svg>
        当前教材：现代西班牙语1
      </span>
      <span class="badge badge--yellow">🔥 连续学习 3 天</span>

      <button class="icon-btn" aria-label="通知">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
      </button>

      <span class="topbar__avatar">我</span>
    </div>
  </header>
</template>
