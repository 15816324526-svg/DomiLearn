<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/request'
import { getImitationReport, listImitationHistory, listImitationPassages, retryImitationReport } from '@/api/imitation'
import type { ImitationHistory, ImitationPassage, ImitationReport } from '@/types/imitation'

defineOptions({ name: 'ImitationReportView' })
const route = useRoute()
const router = useRouter()
const history = ref<ImitationHistory[]>([])
const currentPassages = ref<ImitationPassage[]>([])
const selectedId = ref<string | null>(null)
const report = ref<ImitationReport | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')

const selected = computed(() => history.value.find((item) => item.id === selectedId.value) ?? null)
const groups = computed(() => {
  const grouped = new Map<string, ImitationHistory[]>()
  for (const item of history.value) {
    const key = `${item.lesson_number} · ${item.title} · ${item.passage_id}`
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(item)
  }
  return [...grouped]
})
const canRepeat = computed(() => selected.value && currentPassages.value.some((item) => item.id === selected.value?.passage_id && item.ready))

function errorText(cause: unknown): string {
  if (cause instanceof ApiError) return `${cause.status ? `HTTP ${cause.status} · ` : ''}${cause.message}`
  return cause instanceof Error ? cause.message : '读取学习报告失败'
}

async function openRound(roundId: string) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  selectedId.value = roundId
  report.value = null
  try {
    const item = history.value.find((entry) => entry.id === roundId)
    if (item?.status === 'completed') report.value = await getImitationReport(roundId)
    await router.replace({ path: '/imitation/report', query: { round: roundId } })
  } catch (cause) { error.value = errorText(cause) }
  finally { busy.value = false }
}

async function retryReport() {
  if (!selectedId.value || busy.value) return
  busy.value = true
  error.value = ''
  try { report.value = await retryImitationReport(selectedId.value) }
  catch (cause) { error.value = errorText(cause) }
  finally { busy.value = false }
}

onMounted(async () => {
  try {
    history.value = await listImitationHistory()
    try { currentPassages.value = await listImitationPassages() } catch { currentPassages.value = [] }
    const wanted = typeof route.query.round === 'string' ? route.query.round : history.value.find((item) => item.status === 'completed')?.id
    if (wanted) await openRound(wanted)
  } catch (cause) { error.value = errorText(cause) }
  finally { loading.value = false }
})

function dateLabel(value: string | null): string { return value ? new Date(value).toLocaleString('zh-CN') : '进行中' }
</script>

<template>
  <div class="reports-page">
    <div v-if="error" class="reports-alert" role="alert"><span>{{ error }}</span><button type="button" aria-label="关闭错误提示" @click="error = ''">×</button></div>
    <header class="reports-head"><div><p class="text-dim">学习报告</p><h1>课文仿写记录</h1><p>每一轮和每次提交都会保存。你可以回看旧记录，或从同一篇教材课文再次练习。</p></div><RouterLink class="btn btn--ghost" to="/imitation">选择课文</RouterLink></header>
    <div v-if="loading" class="card reports-pad">正在读取练习记录…</div>
    <div v-else-if="!history.length" class="card reports-pad">尚无仿写记录。<RouterLink to="/imitation">去选择一篇课文</RouterLink></div>
    <div v-else class="reports-layout">
      <aside class="card reports-pad reports-list">
        <h2 class="card__title">历史轮次</h2>
        <div v-for="[key, items] in groups" :key="key" class="reports-group"><h3>第 {{ items[0].lesson_number }} 课 · {{ items[0].title }}</h3>
          <button v-for="(item, index) in items" :key="item.id" type="button" :class="{ selected: item.id === selectedId }" @click="openRound(item.id)">
            第 {{ items.length - index }} 轮 · {{ dateLabel(item.completed_at || item.created_at) }}<small>{{ item.status === 'completed' ? '已完成' : `进行中 ${item.completed_count}/${item.total}` }}</small>
          </button>
        </div>
      </aside>
      <div class="reports-detail">
        <section v-if="selected" class="card reports-pad">
          <div class="reports-title"><div><h2>第 {{ selected.lesson_number }} 课 · {{ selected.title }}</h2><p class="text-dim">{{ dateLabel(selected.completed_at || selected.created_at) }} · {{ selected.completed_count }} / {{ selected.total }} 句</p></div><RouterLink v-if="selected.status === 'active'" class="btn btn--primary" :to="{ path: '/imitation', query: { round: selected.id } }">继续本轮</RouterLink><RouterLink v-else-if="canRepeat" class="btn btn--ghost" :to="{ path: '/imitation', query: { passage: selected.passage_id } }">再次仿写这篇课文</RouterLink></div>
          <template v-if="report">
            <div v-if="report.error" class="reports-warning">{{ report.error }}</div>
            <div v-if="report.status !== 'ready' || report.memory_status !== 'ready'" class="reports-pending"><span>{{ report.status === 'failed' ? '报告生成失败，练习记录已保存。' : report.memory_status !== 'ready' ? '报告已保存，记忆整理仍需重试。' : '报告正在生成。' }}</span><button class="btn btn--ghost" type="button" :disabled="busy" @click="retryReport">重试生成</button></div>
            <p v-if="report.summary" class="reports-summary">{{ report.summary }}</p>
            <div class="reports-stats"><div><strong>{{ selected.total }}</strong><span>完成句子</span></div><div><strong>{{ report.counts.first_pass }}</strong><span>首次用对</span></div><div><strong>{{ report.counts.revised }}</strong><span>修改后通过</span></div><div><strong>{{ report.counts.alternative }}</strong><span>正确替代表达</span></div><div><strong>{{ report.counts.manual_pass }}</strong><span>手动通过</span></div></div>
            <div class="reports-panels"><section><h3>本轮用过的教材句式</h3><p v-if="!report.used_patterns.length" class="text-dim">暂无记录</p><ul><li v-for="pattern in report.used_patterns" :key="pattern">{{ pattern }}</li></ul></section><section><h3>仍可练习的句式</h3><p v-if="!report.unobserved_patterns.length && !report.weak_patterns.length" class="text-dim">暂无记录</p><ul><li v-for="pattern in report.weak_patterns" :key="`weak-${pattern}`">{{ pattern }} · 尝试后仍需改进</li><li v-for="pattern in report.unobserved_patterns" :key="`open-${pattern}`">{{ pattern }} · 本轮未观察到</li></ul></section></div>
            <section v-if="report.recurring_issues.length" class="reports-section"><h3>反复出现的问题</h3><ul><li v-for="issue in report.recurring_issues" :key="issue">{{ issue }}</li></ul></section>
            <section v-if="report.comparison" class="reports-section"><h3>与上次相比</h3><p>{{ report.comparison }}</p></section>
            <section v-if="report.next_suggestions.length" class="reports-section"><h3>下轮建议</h3><ul><li v-for="suggestion in report.next_suggestions" :key="suggestion">{{ suggestion }}</li></ul></section>
            <section class="reports-section"><h3>逐句记录</h3><details v-for="(sentence, index) in report.attempts_by_sentence" :key="sentence.sentence_id" class="reports-sentence"><summary>第 {{ index + 1 }} 句 · {{ sentence.speaker ? `${sentence.speaker}：` : '' }}{{ sentence.chinese_text }}</summary><p class="text-dim">教材句式：{{ sentence.expected_pattern }}</p><div v-for="attempt in sentence.attempts" :key="attempt.id" class="reports-attempt"><strong>{{ attempt.answer || '手动通过' }}</strong><p>{{ attempt.feedback?.explanation || '等待模型重试' }}</p><small>原文显示：{{ attempt.source_mode }} · {{ attempt.hint_viewed ? '已看提示' : '未看提示' }}</small></div></details></section>
            <p class="text-dim reports-usage">本轮模型返回用量：{{ report.model_usage.input_tokens }} 输入 Token、{{ report.model_usage.output_tokens }} 输出 Token（{{ report.model_usage.calls }} 次有用量记录的调用）。</p>
          </template>
          <p v-else-if="selected.status === 'completed'" class="text-dim">正在读取报告…</p>
        </section>
        <section v-else class="card reports-pad">从左侧选择一轮记录。</section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-page{max-width:1450px}.reports-alert{display:flex;justify-content:space-between;gap:16px;background:#fff0ec;color:#9e362b;padding:14px 18px;border-radius:10px;margin-bottom:18px}.reports-alert button{border:0;background:none;color:inherit;font-size:24px;cursor:pointer}.reports-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:22px}.reports-head h1{margin:3px 0 8px}.reports-pad{padding:25px}.reports-layout{display:grid;grid-template-columns:minmax(270px,340px) minmax(0,1fr);gap:22px;align-items:start}.reports-list{max-height:80vh;overflow:auto}.reports-group{border-top:1px solid #e9e9e6;margin-top:16px;padding-top:10px}.reports-group h3{font-size:15px}.reports-group button{display:block;width:100%;text-align:left;border:0;border-radius:8px;background:transparent;padding:10px;cursor:pointer;color:#303840}.reports-group button.selected{background:#f0f3f4;font-weight:700}.reports-group small{display:block;color:#778391;margin-top:4px}.reports-title{display:flex;justify-content:space-between;gap:16px;align-items:start}.reports-title h2{margin:0}.reports-warning{background:#fff0ec;color:#9e362b;padding:12px;border-radius:8px}.reports-pending{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:15px 0}.reports-summary{font-size:18px;line-height:1.7}.reports-stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin:20px 0}.reports-stats div{background:#f7f8f7;border-radius:9px;padding:12px;text-align:center}.reports-stats strong{display:block;font-size:25px}.reports-stats span{font-size:12px;color:#778391}.reports-panels{display:grid;grid-template-columns:1fr 1fr;gap:15px}.reports-panels section{border:1px solid #e8eae8;border-radius:10px;padding:15px}.reports-panels h3,.reports-section h3{margin:0 0 10px}.reports-section{margin-top:24px}.reports-sentence{border-top:1px solid #e8eae8;padding:13px 0}.reports-sentence summary{cursor:pointer;font-weight:600}.reports-attempt{border-left:3px solid #dbe5dc;padding:7px 13px;margin:10px 0}.reports-attempt p{margin:5px 0}.reports-attempt small{color:#788391}.reports-usage{margin-top:28px;font-size:12px}@media(max-width:900px){.reports-layout,.reports-panels{grid-template-columns:1fr}.reports-stats{grid-template-columns:repeat(2,1fr)}.reports-head,.reports-title{flex-direction:column}}
</style>
