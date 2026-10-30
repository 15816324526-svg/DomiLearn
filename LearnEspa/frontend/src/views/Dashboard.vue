<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { CalendarDay, Stage } from '@/types'
import { mockCalendar, mockCalendarMonth, mockDashboardToday, mockMainline } from '@/mock'
import { getModelSettings, testModelSettings } from '@/api/imitation'
import { ApiError } from '@/api/request'
import type { ModelSettings } from '@/types/imitation'

const activeModel = ref<ModelSettings | null>(null)
const modelDraft = reactive({ model_id: '', url: '', api_key: '' })
const testingModel = ref(false)
const modelError = ref('')
const modelSuccess = ref('')

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    const status = error.code.toString().match(/^MODEL_HTTP_(\d+)$/)?.[1]
    return `${status ? `HTTP ${status} · ` : error.status && !String(error.code).includes('NETWORK') && !String(error.code).includes('TIMEOUT') ? `HTTP ${error.status} · ` : ''}${error.message}`
  }
  return error instanceof Error ? error.message : '连接失败，请稍后重试'
}

async function loadModel() {
  try {
    activeModel.value = await getModelSettings()
    modelDraft.model_id = activeModel.value.model_id
    modelDraft.url = activeModel.value.url
    modelDraft.api_key = ''
  } catch (error) {
    modelError.value = errorText(error)
  }
}

function switchModel() {
  modelDraft.model_id = ''
  modelDraft.url = ''
  modelDraft.api_key = ''
  modelError.value = ''
  modelSuccess.value = ''
}

async function testConnection() {
  if (testingModel.value) return
  modelError.value = ''
  modelSuccess.value = ''
  testingModel.value = true
  try {
    activeModel.value = await testModelSettings({ ...modelDraft })
    modelDraft.api_key = ''
    modelSuccess.value = 'HTTP 200 · 测试成功，服务可用'
  } catch (error) {
    modelError.value = errorText(error)
  } finally {
    testingModel.value = false
  }
}

onMounted(loadModel)

/* ---------- 学习阶段文案映射 ---------- */
const stageLabels: Record<Stage, string> = {
  'vocab-choice': '释义选择 (Opción múltiple)',
  'vocab-dictation': '中文默写西语 (Traducción inversa)',
  imitation: '课文仿写 (Imitación)',
  report: '学习报告 (Informe)',
}

/* ---------- 日历圆点：状态 → 样式类 ---------- */
function dayClass(day: CalendarDay): string[] {
  const cls: string[] = []
  if (!day.inMonth) cls.push('cal__day--muted')
  if (day.status === 'checked') cls.push('cal__day--blue')
  if (day.status === 'partial') cls.push('cal__day--yellow')
  if (day.status === 'complete') cls.push('cal__day--green')
  if (day.isToday) cls.push('cal__day--today')
  return cls
}

/* ---------- 进度百分比 ---------- */
const wordPercent = computed(() =>
  Math.round((mockMainline.wordStats.learned / mockMainline.wordStats.total) * 100)
)
const sentencePercent = computed(() =>
  Math.round((mockMainline.sentenceStats.completed / mockMainline.sentenceStats.total) * 100)
)

const weekdays = ['一', '二', '三', '四', '五', '六', '日']
</script>

<template>
  <!-- ============ 学习提醒 ============ -->
  <!-- API: GET /api/dashboard/today -->
  <section class="card notice">
    <div class="notice__body">
      <div class="notice__title">
        <h2 class="card__title">学习提醒</h2>
        <span class="badge badge--yellow">进行中</span>
      </div>
      <p class="notice__text">{{ mockDashboardToday.message }}</p>
      <div class="notice__meta">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 3" />
        </svg>
        建议用时 {{ mockDashboardToday.minutes }} 分钟&nbsp;&nbsp;·&nbsp;&nbsp;{{ mockDashboardToday.taskName }}
      </div>
    </div>
    <RouterLink class="btn btn--ghost" to="/imitation">进入仿写练习 →</RouterLink>
  </section>

  <div class="home-grid">

    <!-- ============ 学习日历 ============ -->
    <!-- API: GET /api/calendar?month=2024-05 -->
    <section class="card">
      <div class="card__head" style="justify-content: space-between">
        <h2 class="card__title">学习日历<span class="en">Calendario</span></h2>
        <span class="badge badge--green">✓ 今日已打卡</span>
      </div>
      <div class="text-dim" style="font-size: var(--fs-sm)">{{ mockCalendarMonth }}</div>

      <div class="cal__grid">
        <div v-for="w in weekdays" :key="w" class="cal__week">{{ w }}</div>

        <div
          v-for="(day, i) in mockCalendar"
          :key="i"
          class="cal__day"
          :class="dayClass(day)"
        >
          {{ day.day }}
          <span v-if="day.status !== 'none'" class="dot"></span>
        </div>
        <!-- 补齐最后一行（5 月共 33 格，补 2 个空位对齐 35 格） -->
        <div></div><div></div>
      </div>

      <div class="card__foot">
        <span class="muted-legend">
          <span class="dot" style="width:7px;height:7px;background:var(--tint-blue-dot)"></span>已打卡
        </span>
        <span class="muted-legend">
          <span class="dot" style="width:7px;height:7px;background:var(--tint-yellow-dot)"></span>部分完成
        </span>
        <span class="muted-legend">
          <span class="dot" style="width:7px;height:7px;background:var(--tint-green-dot)"></span>完整章节
        </span>
        <span style="margin-left:auto">保持每日节奏，语言学习在于润物细无声。</span>
      </div>
    </section>

    <!-- ============ 当前学习 ============ -->
    <!-- API: GET /api/study/mainline -->
    <section class="card">
      <div class="card__head" style="justify-content: space-between">
        <h2 class="card__title">当前学习<span class="en">Progreso</span></h2>
        <span class="badge">主进度</span>
      </div>

      <div class="study__info">
        <div class="study__row"><span class="k">当前教材</span><span class="v">{{ mockMainline.textbook }}</span></div>
        <div class="study__row"><span class="k">当前章节</span><span class="v">{{ mockMainline.chapter }}</span></div>
        <div class="study__row">
          <span class="k">学习阶段</span>
          <span class="v">{{ stageLabels[mockMainline.stage] }}</span>
        </div>
      </div>

      <div class="progress" style="margin-bottom: 14px">
        <div style="flex:1">
          <div class="progress__label">单词掌握</div>
          <div class="progress__track">
            <div class="progress__fill" :style="{ width: wordPercent + '%' }"></div>
          </div>
        </div>
        <span class="progress__meta">
          {{ mockMainline.wordStats.learned }} / {{ mockMainline.wordStats.total }} 词&nbsp;&nbsp;
          <b style="color:var(--ink-1)">{{ wordPercent }}%</b>
        </span>
      </div>

      <div class="progress">
        <div style="flex:1">
          <div class="progress__label">课文仿写</div>
          <div class="progress__track">
            <div class="progress__fill" :style="{ width: sentencePercent + '%' }"></div>
          </div>
        </div>
        <span class="progress__meta">
          {{ mockMainline.sentenceStats.completed }} / {{ mockMainline.sentenceStats.total }} 句&nbsp;&nbsp;
          <b style="color:var(--ink-1)">{{ sentencePercent }}%</b>
        </span>
      </div>

      <div style="margin-top: 24px">
        <RouterLink class="btn btn--primary btn--lg" to="/vocabulary">继续当前学习 →</RouterLink>
      </div>

      <div class="study__switch">
        <span class="t">选择其他章节</span>
        <span class="text-dim">按计划逐章推进中</span>
      </div>
      <p class="study__note">仅将当前选定章节设为主线路径，其他章节可归档或处于待开启状态。</p>
    </section>

  </div>

  <section class="card model-service" aria-labelledby="model-service-title">
    <div class="card__head model-service__head">
      <div>
        <h2 id="model-service-title" class="card__title">设置模型服务</h2>
        <p class="text-dim">1.0 支持 DeepSeek 官方 API。连接测试会发送一条很短的真实请求。</p>
      </div>
      <button class="btn btn--ghost" type="button" @click="switchModel">切换服务</button>
    </div>
    <p v-if="activeModel?.has_api_key" class="model-service__active">
      当前生效：{{ activeModel.model_id }} · {{ activeModel.url }} · API Key 已安全保存
    </p>
    <div v-if="modelError" class="model-service__alert" role="alert">
      <span>{{ modelError }}</span>
      <button type="button" aria-label="关闭错误提示" @click="modelError = ''">×</button>
    </div>
    <div v-if="modelSuccess" class="model-service__success" role="status">{{ modelSuccess }}</div>
    <div class="model-service__fields">
      <label>Model ID<input v-model.trim="modelDraft.model_id" class="field" autocomplete="off" placeholder="填写 DeepSeek 官方模型 ID" /></label>
      <label>URL<input v-model.trim="modelDraft.url" class="field" autocomplete="url" placeholder="https://api.deepseek.com" /></label>
      <label>API Key<input v-model="modelDraft.api_key" class="field" type="password" autocomplete="new-password" placeholder="填写后只由后端安全保存" /></label>
    </div>
    <button class="btn btn--primary" type="button" :disabled="testingModel || !modelDraft.model_id || !modelDraft.url || !modelDraft.api_key" @click="testConnection">
      {{ testingModel ? '正在测试连接…' : '填写完毕，点击测试连接' }}
    </button>
    <p class="text-dim model-service__note">测试失败时，旧服务继续生效；草稿会留在输入框中供你修改。</p>
  </section>
</template>

<style scoped>
.model-service { margin-top: 30px; padding: 28px 34px; }
.model-service__head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.model-service__head p { margin: 8px 0 0; font-size: var(--fs-sm); }
.model-service__active { padding: 12px 16px; border-radius: 10px; background: #f3f8f3; color: #326746; overflow-wrap: anywhere; }
.model-service__fields { display: grid; gap: 16px; max-width: 720px; margin: 22px 0; }
.model-service__fields label { display: grid; gap: 7px; font-weight: 600; }
.model-service__fields input { width: 100%; font-weight: 400; }
.model-service__alert, .model-service__success { padding: 12px 16px; border-radius: 10px; margin: 14px 0; }
.model-service__alert { display: flex; align-items: start; justify-content: space-between; gap: 14px; background: #fff1ed; color: #a13827; }
.model-service__alert button { border: 0; background: transparent; color: inherit; font-size: 24px; line-height: 1; cursor: pointer; }
.model-service__success { background: #eef8f0; color: #286342; }
.model-service__note { margin: 14px 0 0; font-size: var(--fs-sm); }
@media (max-width: 700px) { .model-service { padding: 20px; } .model-service__head { flex-direction: column; } }
</style>
