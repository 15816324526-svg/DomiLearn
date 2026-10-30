<script setup lang="ts">
/** 全局轻提示，挂在 App.vue 上，任何页面通过 useUiStore().showToast() 调用 */

import { useUiStore } from '@/stores/ui'

defineOptions({ name: 'AppToast' })

const ui = useUiStore()
</script>

<template>
  <div class="toast" :class="{ 'is-show': ui.visible }">{{ ui.message }}</div>
</template>
