<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AccentKeypad from '@/components/AccentKeypad.vue'
import { splitSource, insertAt } from '@/utils/text'
import { ApiError } from '@/api/request'
import { advanceImitation, getImitationPreferences, getImitationRound, listImitationPassages, saveImitationDraft, setImitationPreferences, startImitationRound, submitImitationAnswer } from '@/api/imitation'
import type { ImitationPassage, ImitationRound, SourceMode } from '@/types/imitation'

defineOptions({ name: 'ImitationWorkspaceView' })
const route = useRoute()
const router = useRouter()
const passages = ref<ImitationPassage[]>([])
const practice = ref<ImitationRound | null>(null)
const draft = ref('')
const mode = ref<SourceMode>('masked')
const hintViewed = ref(false)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)
let saveTimer: ReturnType<typeof setTimeout> | undefined
let pendingRequestId: string | null = null
let applyingRound = false

const grouped = computed(() => {
  const result = new Map<number, ImitationPassage[]>()
  for (const item of passages.value) {
    if (!result.has(item.lesson_number)) result.set(item.lesson_number, [])
    result.get(item.lesson_number)!.push(item)
  }
  return [...result].sort((a, b) => a[0] - b[0])
})
const segments = computed(() => practice.value ? splitSource(practice.value.source_text, practice.value.source_highlights) : [])

function errorText(cause: unknown): string {
  if (cause instanceof ApiError) {
    const upstream = String(cause.code).match(/^MODEL_HTTP_(\d+)$/)?.[1]
    const prefix = upstream ? `HTTP ${upstream} · ` : cause.status && !/NETWORK|TIMEOUT/.test(String(cause.code)) ? `HTTP ${cause.status} · ` : ''
    return prefix + cause.message
  }
  return cause instanceof Error ? cause.message : '请求失败，请重试'
}

function applyRound(value: ImitationRound, keepMode = false) {
  applyingRound = true
  practice.value = value
  draft.value = value.draft
  applyingRound = false
  if (!keepMode) mode.value = value.default_source_mode
  pendingRequestId = [...value.attempts].reverse().find((item) => item.status === 'pending' && item.answer === value.draft)?.request_id ?? null
}

async function openPassage(passageId: string) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const value = await startImitationRound(passageId)
    applyRound(value)
    hintViewed.value = false
    await router.replace({ path: '/imitation', query: { round: value.id } })
  } catch (cause) { error.value = errorText(cause) }
  finally { busy.value = false }
}

onMounted(async () => {
  try {
    const [items, preference] = await Promise.all([listImitationPassages(), getImitationPreferences()])
    passages.value = items
    mode.value = preference.default_source_mode
    if (typeof route.query.round === 'string') applyRound(await getImitationRound(route.query.round))
    else if (typeof route.query.passage === 'string') await openPassage(route.query.passage)
  } catch (cause) { error.value = errorText(cause) }
  finally { loading.value = false }
})

async function saveDraft(showNotice = false): Promise<boolean> {
  if (!practice.value || practice.value.status !== 'active') return false
  if (saveTimer) clearTimeout(saveTimer)
  try {
    await saveImitationDraft(practice.value.id, draft.value)
    if (showNotice) notice.value = '草稿已保存，可以稍后继续。'
    return true
  } catch (cause) { error.value = errorText(cause); return false }
}

watch(draft, (value, previous) => {
  if (applyingRound || !practice.value || practice.value.status !== 'active' || value === previous) return
  pendingRequestId = null
  notice.value = ''
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { void saveDraft() }, 450)
}, { flush: 'sync' })

async function submit() {
  if (!practice.value || busy.value || !draft.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    if (!(await saveDraft())) return
    const requestId = pendingRequestId ?? crypto.randomUUID()
    pendingRequestId = requestId
    applyRound(await submitImitationAnswer(practice.value.id, {
      request_id: requestId, answer: draft.value, source_mode: mode.value, hint_viewed: hintViewed.value,
    }), true)
    pendingRequestId = null
  } catch (cause) { error.value = errorText(cause) }
  finally { busy.value = false }
}

async function nextSentence(manualPass = false) {
  if (!practice.value || busy.value) return
  const roundId = practice.value.id
  busy.value = true
  error.value = ''
  try {
    const value = await advanceImitation(roundId, manualPass)
    applyRound(value, true)
    hintViewed.value = false
    if (value.status === 'completed') await router.push({ path: '/imitation/report', query: { round: roundId } })
  } catch (cause) { error.value = errorText(cause) }
  finally { busy.value = false }
}

async function saveDefaultMode() {
  try { await setImitationPreferences(mode.value); notice.value = '已设为以后练习的默认遮挡方式。' }
  catch (cause) { error.value = errorText(cause) }
}

function onInsert(char: string) {
  const el = textarea.value
  if (!el) return
  const start = el.selectionStart ?? draft.value.length
  draft.value = insertAt(draft.value, char, start, el.selectionEnd ?? start)
  nextTick(() => { el.focus(); el.setSelectionRange(start + char.length, start + char.length) })
}

function readOriginal() {
  if (!practice.value) return
  if (!('speechSynthesis' in window)) { error.value = '当前浏览器不支持本地朗读。'; return }
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(practice.value.source_text)
  utterance.lang = 'es-ES'
  window.speechSynthesis.speak(utterance)
}
onBeforeUnmount(() => {
  if (saveTimer) {
    clearTimeout(saveTimer)
    void saveDraft()
  }
})
</script>

<template>
  <div class="imitation-page">
    <div v-if="error" class="imitation-error" role="alert"><span>{{ error }}</span><button type="button" aria-label="关闭错误提示" @click="error = ''">×</button></div>
    <div v-if="notice" class="imitation-notice" role="status">{{ notice }}</div>
    <div v-if="loading" class="card imitation-pad">正在读取教材课文…</div>
    <template v-else-if="!practice">
      <header class="imitation-intro"><p class="text-dim">课文仿写</p><h1>选择一篇课文</h1><p>AI 将参考教材句式与学习记录，编排新的中文情景。练习时每次只显示一句。</p></header>
      <section v-for="[lessonNumber, items] in grouped" :key="lessonNumber" class="card imitation-pad imitation-chapter">
        <h2>第 {{ lessonNumber }} 课</h2>
        <div v-for="item in items" :key="item.id" class="imitation-passage">
          <div><strong>{{ item.title }}</strong><p class="text-dim">{{ item.sentence_count }} 句<span v-if="item.issue"> · {{ item.issue }}</span></p></div>
          <button class="btn btn--ghost" type="button" :disabled="!item.ready || busy" @click="openPassage(item.id)">{{ busy ? '编排中…' : item.active_round_id ? '继续练习' : item.ready ? '开始仿写' : '尚需核查' }}</button>
        </div>
      </section>
      <div v-if="!grouped.length && !error" class="card imitation-pad">目前没有可用课文，请先在教材目录确认解析结果。</div>
    </template>
    <template v-else>
      <div class="imitation-topline"><button class="btn btn--ghost" type="button" @click="practice = null; router.replace('/imitation')">← 选择其他课文</button><span>第 {{ practice.lesson_number }} 课 · {{ practice.title }} · {{ practice.current_index }} / {{ practice.total }} 句已完成</span></div>
      <div class="imitation-columns">
        <section class="card imitation-pad">
          <div class="card__head imitation-head"><h2 class="card__title">教材原文</h2><select v-model="mode" class="field" aria-label="原文遮挡方式"><option value="normal">完整显示</option><option value="masked">重点遮挡</option><option value="hidden">完全遮挡</option></select></div>
          <button class="imitation-link" type="button" @click="saveDefaultMode">设为以后默认方式</button>
          <div v-if="mode === 'hidden'" class="imitation-hidden">原文已遮挡，可随时切换显示方式。</div>
          <div v-else class="source__text imitation-source-text"><template v-for="(segment, index) in segments" :key="index"><span v-if="segment.hit && mode === 'masked'" class="masked">{{ segment.text }}</span><mark v-else-if="segment.hit">{{ segment.text }}</mark><template v-else>{{ segment.text }}</template></template></div>
          <button class="btn btn--ghost imitation-read" type="button" @click="readOriginal">本地朗读原文</button>
        </section>
        <section class="card imitation-pad">
          <div class="card__head imitation-head"><h2 class="card__title">逐句仿写</h2><span class="badge">第 {{ practice.current_index + 1 }} / {{ practice.total }} 句</span></div>
          <p class="imitation-background">{{ practice.background }}</p>
          <div v-if="practice.current_sentence" class="imitation-chinese"><span v-if="practice.current_sentence.speaker">{{ practice.current_sentence.speaker }}：</span>{{ practice.current_sentence.chinese_text }}</div>
          <button v-if="practice.current_sentence?.hint && !hintViewed" class="imitation-link" type="button" @click="hintViewed = true">查看一句情境提示</button>
          <p v-if="practice.current_sentence?.hint && hintViewed" class="text-dim">提示：{{ practice.current_sentence.hint }}</p>
          <textarea ref="textarea" v-model="draft" class="field imitation-answer" rows="5" placeholder="请写一句西语。提交前会先保存原答案。" :disabled="busy || practice.status === 'completed'" />
          <AccentKeypad @insert="onInsert" />
          <div class="imitation-actions"><button class="btn btn--ghost" type="button" :disabled="busy" @click="saveDraft(true)">暂时保存</button><button class="btn btn--primary" type="button" :disabled="busy || !draft.trim() || practice.status === 'completed'" @click="submit">{{ busy ? '正在处理…' : '提交本句' }}</button></div>
          <div v-if="practice.feedback" class="imitation-feedback" :class="`imitation-feedback--${practice.feedback.verdict}`"><strong>{{ practice.feedback.verdict === 'passed' ? '本句通过' : practice.feedback.verdict === 'alternative' ? '表达正确，使用了另一种说法' : '还需修改' }}</strong><p>{{ practice.feedback.explanation }}</p><p v-if="practice.feedback.revision">可以这样表达：{{ practice.feedback.revision }}</p></div>
          <p v-if="practice.rejection_count" class="text-dim">本句未通过 {{ practice.rejection_count }} 次；模型请求失败不会计入。</p>
          <div class="imitation-actions"><button v-if="practice.can_next" class="btn btn--primary" type="button" :disabled="busy" @click="nextSentence(false)">{{ practice.current_index + 1 === practice.total ? '完成并查看报告' : '进入下一句 →' }}</button><button v-if="practice.can_manual_pass" class="btn btn--ghost" type="button" :disabled="busy" @click="nextSentence(true)">手动通过并进入下一句</button></div>
          <details v-if="practice.attempts.length" class="imitation-attempts"><summary>本句提交记录（{{ practice.attempts.length }}）</summary><div v-for="attempt in practice.attempts" :key="attempt.id"><p>{{ attempt.answer || '手动通过' }}</p><small>{{ attempt.feedback?.explanation || '已保存，等待重试判定' }} · {{ attempt.source_mode }}{{ attempt.hint_viewed ? ' · 使用提示' : '' }}</small></div></details>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.imitation-page{max-width:1500px}.imitation-pad{padding:25px}.imitation-error{display:flex;justify-content:space-between;gap:16px;background:#fff0ec;color:#9e362b;padding:14px 18px;border-radius:10px;margin-bottom:18px}.imitation-error button{border:0;background:none;color:inherit;font-size:24px;cursor:pointer}.imitation-notice{background:#eef8f0;color:#276341;padding:12px 16px;border-radius:10px;margin-bottom:18px}.imitation-intro{margin-bottom:25px}.imitation-intro h1{margin:4px 0 8px}.imitation-chapter{margin-bottom:18px}.imitation-chapter h2{margin:0 0 10px}.imitation-passage{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:15px 0;border-top:1px solid #e9e9e6}.imitation-passage p{margin:5px 0 0}.imitation-topline{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:16px}.imitation-columns{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px;align-items:start}.imitation-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.imitation-head select{width:auto}.imitation-link{border:0;background:none;color:#47739c;cursor:pointer;padding:6px 0}.imitation-source-text{white-space:pre-line;line-height:1.9;margin:20px 0}.imitation-hidden{padding:35px 10px;color:#8b929d;text-align:center}.imitation-read{width:100%}.imitation-background{color:#687789;background:#f6f7f8;border-radius:9px;padding:10px 13px}.imitation-chinese{font-size:21px;font-weight:600;line-height:1.65;margin:22px 0}.imitation-answer{width:100%;resize:vertical}.imitation-actions{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end;margin-top:14px}.imitation-feedback{padding:15px;border-radius:10px;margin-top:20px;background:#fff4e4}.imitation-feedback p{margin:8px 0 0}.imitation-feedback--passed,.imitation-feedback--alternative{background:#eef8f0}.imitation-attempts{margin-top:22px;border-top:1px solid #ececec;padding-top:14px}.imitation-attempts>div{border-top:1px solid #eee;padding:6px 0}.imitation-attempts p{margin:6px 0}.imitation-attempts small{color:#718090}@media(max-width:900px){.imitation-columns{grid-template-columns:1fr}.imitation-topline{flex-direction:column;align-items:flex-start}}
</style>
