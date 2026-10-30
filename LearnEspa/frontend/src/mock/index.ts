/**
 * 原型阶段的假数据集中在这里。
 * 第二步接入后端后，把本文件替换为 src/api/*.ts 的真实请求即可，
 * 视图组件不用改（因为它们只依赖 types.ts 里的类型）。
 */

import type {
  DashboardToday,
  CalendarDay,
  Mainline,
  SidebarTask,
  CheckinStatus,
  VocabOverview,
  MeaningWord,
  DictationWord,
  VocabSummary,
  ImitationTask,
  ImitationEvaluation,
  LearningReport,
} from '@/types'

/* ---------- 首页 · 今日概览 ---------- */
// API: GET /api/dashboard/today
export const mockDashboardToday: DashboardToday = {
  stage: 'imitation',
  message:
    '第 1 课单词已经完成，课文仿写尚未完成。你可以继续上次的学习，也可以切换到其他章节。',
  minutes: 15,
  taskName: '仿写练习：自我介绍与基础句型（Lección 1）',
}

/* ---------- 首页 · 打卡日历（2024 年 5 月） ---------- */
// API: GET /api/calendar?month=2024-05
const rawCalendar: Array<[number, boolean, CheckinStatus, boolean]> = [
  // [日期, 是否本月, 状态, 是否今天]
  [29, false, 'none', false],
  [30, false, 'none', false],
  [1, true, 'none', false],
  [2, true, 'checked', false],
  [3, true, 'complete', false],
  [4, true, 'none', false],
  [5, true, 'partial', false],
  [6, true, 'none', false],
  [7, true, 'none', false],
  [8, true, 'checked', false],
  [9, true, 'complete', false],
  [10, true, 'partial', false],
  [11, true, 'complete', true],
  [12, true, 'none', false],
  [13, true, 'none', false],
  [14, true, 'none', false],
  [15, true, 'none', false],
  [16, true, 'none', false],
  [17, true, 'none', false],
  [18, true, 'none', false],
  [19, true, 'none', false],
  [20, true, 'none', false],
  [21, true, 'none', false],
  [22, true, 'none', false],
  [23, true, 'none', false],
  [24, true, 'none', false],
  [25, true, 'none', false],
  [26, true, 'none', false],
  [27, true, 'none', false],
  [28, true, 'none', false],
  [29, true, 'none', false],
  [30, true, 'none', false],
  [31, true, 'none', false],
]

export const mockCalendar: CalendarDay[] = rawCalendar.map(
  ([day, inMonth, status, isToday]) => ({ day, inMonth, status, isToday })
)

export const mockCalendarMonth = '2024年5月'

/* ---------- 首页 · 学习主线 ---------- */
// API: GET /api/study/mainline
export const mockMainline: Mainline = {
  textbook: '现代西班牙语 1',
  chapter: '第 2 课 · En la universidad (在大学)',
  stage: 'vocab-dictation', // 主线停在默写阶段，所以「继续当前学习」进入词汇复习
  wordStats: { learned: 12, total: 120 },
  sentenceStats: { completed: 1, total: 30 },
}

/* ---------- 侧栏 · 今日任务清单 ---------- */
export const mockSidebarTasks: SidebarTask[] = [
  { name: '新词记忆', done: 10, total: 10, tone: 'green', stateText: '已完成' },
  { name: '课文仿写', done: 0, total: 1, tone: 'yellow', stateText: '待完成' },
]

/* ---------- 侧栏 · 待复习词数 ---------- */
export const mockVocabPending = 128

/* ============================================================
   以下为第二步新增的 mock 数据（背单词 3 屏 + 仿写 4 屏）
   字段与 types/index.ts 一一对应，后端联调后由 api/index.ts 接管
   ============================================================ */

/* ---------- 单词学习 · 章节概览 ---------- */
// API: GET /api/chapters/{chapterId}/vocab-overview
export const mockVocabOverview: VocabOverview = {
  chapter: {
    title: '单词背诵 · 第1课',
    description:
      '完成本课单词释义选择和中文默写，系统会记录需要复习的词汇。\n顺序固定：先释义选择，后中文默写，答错的单词会在本轮自动重复。',
    wordCount: 40,
    estimatedMinutes: 10,
  },
}

/* ---------- 单词学习 · 释义选择题库 ---------- */
// API: GET /api/chapters/{chapterId}/words/meaning-quiz
export const mockMeaningWords: MeaningWord[] = [
  {
    id: 'w1', lemma: 'desayunar', pos: 'v.',
    options: ['吃早饭', '吃午饭', '吃晚饭', '睡觉'], answer: 0,
  },
  {
    id: 'w2', lemma: 'universidad', pos: 'f.',
    options: ['图书馆', '大学', '教室', '食堂'], answer: 1,
  },
  {
    id: 'w3', lemma: 'estudiante', pos: 'm./f.',
    options: ['老师', '工人', '学生', '医生'], answer: 2,
  },
  {
    id: 'w4', lemma: 'biblioteca', pos: 'f.',
    options: ['医院', '银行', '书店', '图书馆'], answer: 3,
  },
]

/* ---------- 单词学习 · 中文默写题库 ---------- */
// API: GET /api/chapters/{chapterId}/words/dictation-quiz
export const mockDictationWords: DictationWord[] = [
  { id: 'w1', meaning: '吃早饭', answer: 'desayunar' },
  { id: 'w2', meaning: '大学', answer: 'universidad' },
  { id: 'w3', meaning: '图书馆', answer: 'biblioteca' },
  // 含重音：用于验证「去重音后相同 = 重音问题」这条判定分支
  { id: 'w4', meaning: '课', answer: 'lección' },
]

/* ---------- 单词学习 · 本轮总结 ---------- */
// API: GET /api/vocab-sessions/{sessionId}/summary
export const mockVocabSummary: VocabSummary = {
  summary: {
    description: '你完成了第1课的单词释义选择和中文默写，薄弱词已写入复习池。',
    reviewWords: [
      { id: 'w1', lemma: 'llamarse', meaning: '名叫…', reason: '默写错误 2 次' },
      { id: 'w2', lemma: 'universidad', meaning: '大学', reason: '拼写错误 1 次' },
      { id: 'w3', lemma: 'desayunar', meaning: '吃早饭', reason: '西语输出不稳定' },
    ],
    stableWords: [
      { id: 's1', lemma: 'hola', meaning: '你好', reason: '释义 · 默写均正确' },
      { id: 's2', lemma: 'gracias', meaning: '谢谢', reason: '释义 · 默写均正确' },
      { id: 's3', lemma: 'estudiante', meaning: '学生', reason: '释义 · 默写均正确' },
      { id: 's4', lemma: 'biblioteca', meaning: '图书馆', reason: '释义 · 默写均正确' },
    ],
    stats: { learned: 40, review: 3, stable: 37, accuracy: 92, minutes: 8 },
  },
}

/* ---------- 课文仿写 · 当前任务 ---------- */
// API: GET /api/imitation-tasks/current
export const mockImitationTask: ImitationTask = {
  chapter: '第 1 课 · Lección 1',
  description: '根据左侧原文句式，用右侧情境完成西语仿写。',
  task: {
    position: 1,
    total: 3,
    chinesePrompt:
      '开学第一天，你想向新同学介绍你的朋友 Elena，并说明她的身份和学习内容。请用西语完成这句介绍。',
    targets: [
      { kind: 'word', label: 'universitaria' },
      { kind: 'pattern', label: 'Esta es…' },
      { kind: 'grammar', label: 'ser 第三人称' },
    ],
  },
  sourceText: {
    text:
      'Este es Felipe. Es estudiante universitario.\nÉl estudia en la universidad y aprende español.\n— ¿Eres estudiante?\n— Sí, estudio español en la universidad.',
    highlights: ['Este', 'Felipe', 'Es', 'universitario'],
  },
  keyPoints: [
    'Este es + 人名：介绍他人',
    'ser 的第三人称：es',
    '-ar 动词现在时：estudia / estudio',
  ],
  translation:
    '这是费利佩。他是大学生。他在大学学习并学习西班牙语。——你是学生吗？——是的，我在大学学习西班牙语。',
}

/* ---------- 课文仿写 · AI 分析结果 ---------- */
// API: GET /api/imitation-evaluations/{evaluationId}
export const mockImitationEvaluation: ImitationEvaluation = {
  attempt: {
    position: 1,
    total: 3,
    userAnswer: 'Esta es Elena. Es estudiante universitaria, estudio español en la universidad.',
    submittedAt: '今天 10:32',
  },
  verdicts: [
    { key: 'semantic', label: '语义表达', level: 'pass' },
    { key: 'grammar', label: '语法表达', level: 'weak' },
    { key: 'target', label: '训练目标', level: 'missed' },
  ],
  correct: [
    {
      sentence: 'Esta es Elena. Es estudiante universitaria.',
      comment: '主干句式使用准确，人物介绍和身份表达清晰。',
    },
  ],
  improve: [
    {
      user: 'estudio español',
      expected: 'estudia español',
      explanation:
        '前半句主语是 Elena（第三人称单数），动词应使用 estudia 而不是 estudio。词形问题已记入你的学习状态。',
    },
  ],
  targetMissed: 1,
  targetMissedNote:
    '你的表达意思基本正确，但本次没有使用目标句式来引出人物。该句式已加入复习池，后续仿写中会再次出现。',
  reference: 'Esta es Elena. Es estudiante universitaria.',
}

/* ---------- 学习报告 ---------- */
// API: GET /api/reports/{reportId}
export const mockLearningReport: LearningReport = {
  report: {
    meta: {
      textbook: '现代西班牙语 1',
      chapter: '第 1 课 · Lección 1',
      durationText: '今天 10:21 – 10:35',
      completedText: '今天 10:35',
      imitationStatus: '已完成',
    },
    wordStats: { learned: 40, review: 3, stable: 37 },
    sentenceStats: { total: 3, passed: 1, weak: 2 },
    reviewWords: [
      { name: 'llamarse', note: '默写时出现动词变位错误，后续单词练习中再次出现。', badge: '复习池' },
      { name: 'universidad', note: '拼写不稳定，加入复习池。', badge: '复习池' },
    ],
    patterns: [
      { name: '自我介绍句式', note: '语义表达基本正确，但没有使用本次目标句式。', badge: '复习池' },
    ],
    grammar: [
      { name: '第一人称动词变位', note: '介绍他人时应用第三人称变位（estudia），后续仿写中继续安排。', badge: '强化中' },
    ],
    missedTargets: [
      { name: 'Esta es… 引出人物', note: '本次表达意思正确，但没有使用该目标结构，已加入复习池。', badge: '复习池' },
    ],
  },
}
