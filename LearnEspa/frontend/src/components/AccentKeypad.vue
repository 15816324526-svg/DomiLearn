<script setup lang="ts">
/**
 * 西语特殊字符键盘
 * ------------------------------------------------------------
 * 默写页和仿写页都要用，抽成组件避免重复两遍。
 * 组件本身不碰输入框，只负责「点哪个键」，插入逻辑交给父组件，
 * 因为 input 与 textarea 的光标处理方式不同。
 */
import type { AccentKeypadProps } from '@/types'

const props = withDefaults(defineProps<AccentKeypadProps>(), {
  chars: () => ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡'],
})

const emit = defineEmits<{
  (e: 'insert', char: string): void
}>()

defineOptions({ name: 'AccentKeypad' })

function onKey(char: string) {
  emit('insert', char)
}
</script>

<template>
  <div class="char-keys" aria-label="西语特殊字符">
    <button
      v-for="char in props.chars"
      :key="char"
      type="button"
      class="char-key"
      @click="onKey(char)"
    >
      {{ char }}
    </button>
  </div>
</template>
