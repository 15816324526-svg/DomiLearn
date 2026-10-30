<script setup lang="ts">
import AppTopbar from '@/components/AppTopbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppToast from '@/components/AppToast.vue'
</script>

<template>
  <AppTopbar />

  <div class="layout">
    <AppSidebar />

    <!-- 所有页面视图都渲染在这个 .main 里 -->
    <main class="main">
      <RouterView />
    </main>
  </div>

  <!-- 全局轻提示 -->
  <AppToast />
</template>
