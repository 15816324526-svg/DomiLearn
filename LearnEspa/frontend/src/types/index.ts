/* ============================================================
   DomiLearn 前端数据模型 / TypeScript 类型定义
   ------------------------------------------------------------
   来源：静态原型 domilearn-prototype 中 36 个 data-field 锚点
        与 MOCK 数据结构，一一对应，字段名保持一致。
   用途：Vue3 + TS 项目的 src/types/index.ts
   ============================================================ */

/* ---------- 通用 ---------- */

/** 统一接口返回结构 */
export interface ApiResult<T> {
  code: number | string;
  message: string;
  data: T;
}

/** 学习阶段（贯穿背单词与仿写两条主线） */
export type Stage =
  | 'vocab-choice'    // 释义选择
  | 'vocab-dictation' // 中文默写
  | 'imitation'       // 课文仿写
  | 'report';         // 学习报告

/* ---------- 首页 Dashboard ---------- */

/** 打卡日状态 GET /api/calendar?month=YYYY-MM
 *  none     无记录（不显示圆点）
 *  checked  已打卡（浅蓝）
 *  partial  部分完成（浅黄）
 *  complete 完成整章（浅绿）
 */
export type CheckinStatus = 'none' | 'checked' | 'partial' | 'complete';

export interface CalendarDay {
  /** 1-31 */
  day: number;
  /** 是否为本月日期（补位用的前后月日期为 false） */
  inMonth: boolean;
  status: CheckinStatus;
  /** 是否为今天（叠加描边高亮，与 status 无关） */
  isToday?: boolean;
}

/** 侧栏「今日任务清单」单项 */
export interface SidebarTask {
  name: string;
  done: number;
  total: number;
  /** 决定圆点颜色与完成文案色，只用低饱和色 */
  tone: 'green' | 'yellow' | 'blue' | 'grey';
  stateText: string;
}

/** 今日概览 GET /api/dashboard/today */
export interface DashboardToday {
  stage: Stage;
  /** 顶部学习提醒文案 */
  message: string;
  minutes: number;
  taskName: string;
}

/** 学习主线 GET /api/study/mainline */
export interface Mainline {
  textbook: string;
  chapter: string;
  stage: Stage;
  wordStats: { learned: number; total: number };
  sentenceStats: { completed: number; total: number };
}

/* ---------- 背单词 · 词汇总览 ---------- */

/** GET /api/chapters/{chapterId}/vocab-overview */
export interface VocabOverview {
  chapter: {
    title: string;
    description: string;
    wordCount: number;
    estimatedMinutes: number;
  };
}

/* ---------- 背单词 · 释义选择 ---------- */

/** GET /api/chapters/{chapterId}/words/meaning-quiz → MeaningWord[] */
export interface MeaningWord {
  id: string;
  /** 西语单词 */
  lemma: string;
  /** 词性，如 "v." "f." */
  pos: string;
  /** 四个中文选项，长度固定 4 */
  options: [string, string, string, string];
  /** 正确项下标 0-3 */
  answer: 0 | 1 | 2 | 3;
}

/** 答题过程中本地维护的状态（非接口返回） */
export interface QuizProgress {
  position: number;
  total: number;
  roundErrors: number;
}

/* ---------- 背单词 · 中文默写 ---------- */

/** GET /api/chapters/{chapterId}/words/dictation-quiz → DictationWord[] */
export interface DictationWord {
  id: string;
  /** 中文提示 */
  meaning: string;
  /** 正确西语答案 */
  answer: string;
}

/** 默写判定结果分级（对应三种 UI 状态） */
export type DictationVerdict = 'exact' | 'accent' | 'wrong';

/* ---------- 背单词 · 本轮总结 ---------- */

/** GET /api/vocab-sessions/{sessionId}/summary */
export interface VocabSummary {
  summary: {
    description: string;
    /** 待复习词 */
    reviewWords: WordRef[];
    /** 已掌握的稳定词 */
    stableWords: WordRef[];
    stats: {
      learned: number;
      review: number;
      stable: number;
      accuracy: number;
      minutes: number;
    };
  };
}

export interface WordRef {
  id: string;
  lemma: string;
  /** 中文释义 */
  meaning: string;
  /** 进入复习池的原因，如 "默写错误 2 次" */
  reason?: string;
}

/* ---------- 第一课真实背词会话 ---------- */
export interface StudyQuestion {
  id: string;
  lemma?: string;
  pos?: string;
  options?: string[];
  meaning?: string;
  hint?: string | null;
}

export interface StudyFeedback {
  correct: boolean;
  skipped: boolean;
  submittedAnswer: string | number | null;
  correctAnswer: string;
  correctOptionIndex: number | null;
}

export interface StudySummary {
  learned: number;
  review: number;
  stable: number;
  attempts: number;
  reviewWords: WordRef[];
  stableWords: WordRef[];
}

export interface VocabularyStudyState {
  overview: {
    title: string;
    description: string;
    wordCount: number;
    estimatedMinutes: number;
  };
  session: {
    id: string;
    stage: 'choice' | 'dictation' | 'complete';
    total: number;
    done: number;
    errors: number;
    question: StudyQuestion | null;
    feedback: StudyFeedback | null;
    summary: StudySummary | null;
  };
}

/* ---------- 课文仿写 · 工作台 ---------- */

/** 原文显示模式（前端本地状态，不入库） */
export type SourceMode = 'normal' | 'masked' | 'hidden';

/** GET /api/imitation-tasks/current */
export interface ImitationTask {
  chapter: string;
  /** 仿写说明 */
  description: string;
  task: {
    position: number;
    total: number;
    /** 中文提示语（AI 生成的仿写情境） */
    chinesePrompt: string;
    /** 本句必须用到的目标：词 / 句式 / 语法，不超过 3 个 */
    targets: ImitationTarget[];
  };
  sourceText: {
    /** 参考原文（可含换行符） */
    text: string;
    /** 需要高亮的重点词，UI 渲染成淡黄底；遮挡模式下这些词会被盖住 */
    highlights: string[];
  };
  /** 训练重点说明，默认折叠 */
  keyPoints: string[];
  /** 中文对照，默认折叠 */
  translation: string;
}

export interface ImitationTarget {
  /** 词 / 句式 / 语法 */
  kind: 'word' | 'pattern' | 'grammar';
  label: string;
}

/** 提交仿写 POST /api/imitation-sessions/{id}/submit */
export interface SubmissionPayload {
  sessionId: string;
  taskId: string;
  /** 用户提交的西语句子 */
  text: string;
  submittedAt: string; // ISO8601
}

/* ---------- 课文仿写 · AI 分析 ---------- */

/** 分析状态（轮询 analyzing → analyzed / failed） */
export type AnalysisStatus = 'pending' | 'analyzing' | 'analyzed' | 'failed';

/* ---------- 课文仿写 · 反馈 ---------- */

/** 三档结论：通过 / 需要加强 / 未完成 */
export type VerdictLevel = 'pass' | 'weak' | 'missed';

/** 语义 / 语法 / 训练目标，三者分开判，不合并总分 */
export type VerdictKey = 'semantic' | 'grammar' | 'target';

export interface VerdictItem {
  key: VerdictKey;
  label: string;
  level: VerdictLevel;
}

/** 表达正确的分句 */
export interface EvaluationHighlight {
  sentence: string;
  comment: string;
}

/** 需要修正的一处：用户写法 → 建议写法 */
export interface EvaluationCorrection {
  user: string;
  expected: string;
  explanation: string;
}

/** GET /api/imitation-evaluations/{evaluationId} */
export interface ImitationEvaluation {
  attempt: {
    position: number;
    total: number;
    /** 用户提交的原句 */
    userAnswer: string;
    submittedAt: string;
  };
  /** 三个核心结论卡片 */
  verdicts: VerdictItem[];
  /** 表达正确 */
  correct: EvaluationHighlight[];
  /** 需要加强 */
  improve: EvaluationCorrection[];
  /** 未命中/遗漏的目标数量 */
  targetMissed: number;
  /** 目标未命中的说明文案 */
  targetMissedNote: string;
  /** 参考表达 */
  reference: string;
}

/* ---------- 学习报告 ---------- */

/** 报告中的一条复习项（四种类型结构一致） */
export interface ReviewItem {
  name: string;
  note: string;
  /** 右上角小徽章文案，如 "复习池" "强化中" */
  badge?: string;
}

/** GET /api/reports/{reportId} */
export interface LearningReport {
  report: {
    meta: {
      textbook: string;
      chapter: string;
      /** 展示用时间区间，如 "今天 10:21 – 10:35" */
      durationText: string;
      /** 展示用完成时间，如 "今天 10:35" */
      completedText: string;
      /** 仿写状态文案，如 "已完成" */
      imitationStatus: string;
    };
    wordStats: { learned: number; review: number; stable: number };
    sentenceStats: { total: number; passed: number; weak: number };
    /** 需要复习的单词 */
    reviewWords: ReviewItem[];
    /** 需要加强的句式 */
    patterns: ReviewItem[];
    /** 需要注意的语法 */
    grammar: ReviewItem[];
    /** 未完成的训练目标 */
    missedTargets: ReviewItem[];
  };
}

/* ---------- 组件级 props 类型建议 ---------- */

export interface AppSidebarProps {
  /** 当前高亮的模块 key */
  activeNav: NavKey;
}

/** 侧栏模块 key，与 router 的 meta.nav 一致 */
export type NavKey = 'home' | 'textbook' | 'vocabulary' | 'imitation' | 'report';

/* ---------- 教材 PDF 导入 ---------- */

export type ImportStatus =
  | 'queued'
  | 'processing'
  | 'awaiting_confirmation'
  | 'confirmed'
  | 'failed'
  | 'superseded';

export interface CurrentVersionState {
  id: string;
  displayFilename: string;
  pageCount: number;
  confirmedAt: string;
}

export interface ImportJobState {
  id: string;
  status: ImportStatus;
  displayFilename: string;
  totalPages: number;
  processedPages: number | null;
  elapsedSeconds: number;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  errorCode: string | null;
  errorMessage: string | null;
}

export interface TextbookState {
  id: 'modern-spanish-1';
  title: string;
  currentVersion: CurrentVersionState | null;
  latestJob: ImportJobState | null;
}

export interface ProgressBarProps {
  value: number;
  max: number;
  /** 是否显示 "第 x / y" 文本 */
  showLabel?: boolean;
}

export interface AccentKeypadProps {
  /** 支持的西语特殊字符，默认 á é í ó ú ñ ü ¿ ¡ */
  chars?: string[];
}
