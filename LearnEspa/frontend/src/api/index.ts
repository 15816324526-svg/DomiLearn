/**
 * 业务接口层
 * ------------------------------------------------------------
 * 视图组件只 import 这里的函数，不直接碰 mock 或 fetch。
 * 教材与背词始终连接后端；尚未开发的仿写、报告仍使用演示数据。
 */

import { http, mockDelay, clone, USE_MOCK } from './request'
import type {
  ImitationTask,
  ImitationEvaluation,
  LearningReport,
  TextbookState,
  ImportJobState,
  VocabularyStudyState,
} from '@/types'
import {
  mockImitationTask,
  mockImitationEvaluation,
  mockLearningReport,
} from '@/mock'

/** 课文仿写 · 当前任务 GET /api/imitation-tasks/current */
export function getCurrentImitationTask(): Promise<ImitationTask> {
  if (USE_MOCK) return mockDelay(clone(mockImitationTask))
  return http<ImitationTask>('/imitation-tasks/current')
}

/**
 * 课文仿写 · 提交本句 POST /api/imitation-sessions/{id}/submit
 * @returns evaluationId，用于跳转到反馈页取结果
 */
export function submitImitation(text: string): Promise<{ evaluationId: string }> {
  if (USE_MOCK) return mockDelay({ evaluationId: 'demo-evaluation' }, 300)
  return http<{ evaluationId: string }>('/imitation-sessions/current/submit', {
    method: 'POST',
    body: JSON.stringify({
      taskId: 'current',
      text,
      submittedAt: new Date().toISOString(),
    }),
  })
}

/** 课文仿写 · 分析结果 GET /api/imitation-evaluations/{evaluationId} */
export function getEvaluation(evaluationId = 'demo-evaluation'): Promise<ImitationEvaluation> {
  if (USE_MOCK) return mockDelay(clone(mockImitationEvaluation))
  return http<ImitationEvaluation>(`/imitation-evaluations/${evaluationId}`)
}

/** 学习报告 GET /api/reports/{reportId} */
export function getReport(reportId = 'demo-report'): Promise<LearningReport> {
  if (USE_MOCK) return mockDelay(clone(mockLearningReport))
  return http<LearningReport>(`/reports/${reportId}`)
}

/** 教材目录 GET /api/textbooks/modern-spanish-1（始终连接真实后端） */
export function getTextbookState(): Promise<TextbookState> {
  return http<TextbookState>('/textbooks/modern-spanish-1')
}

/** 上传教材 POST /api/textbooks/modern-spanish-1/imports */
export function uploadTextbook(file: File): Promise<ImportJobState> {
  const body = new FormData()
  body.append('file', file)
  return http<ImportJobState>('/textbooks/modern-spanish-1/imports', { method: 'POST', body })
}

export function getTextbookImport(jobId: string): Promise<ImportJobState> {
  return http<ImportJobState>(`/textbook-imports/${jobId}`)
}

export function confirmTextbookImport(jobId: string): Promise<TextbookState> {
  return http<TextbookState>(`/textbook-imports/${jobId}/confirm`, { method: 'POST' })
}

export function retryTextbookImport(jobId: string): Promise<ImportJobState> {
  return http<ImportJobState>(`/textbook-imports/${jobId}/retry`, { method: 'POST' })
}

/** 已确认教材中可学习的章节。 */
export function getVocabularyLessons(): Promise<Array<{ number: number; title: string }>> {
  return http<Array<{ number: number; title: string }>>('/vocabulary/lessons')
}

export function getVocabularyStudy(lessonNumber = 1): Promise<VocabularyStudyState> {
  return http<VocabularyStudyState>(`/vocabulary/lesson/${lessonNumber}`)
}

export function submitVocabularyAnswer(
  sessionId: string,
  questionId: string,
  answer: string | number | null,
  requestId: string,
  lessonNumber = 1
): Promise<VocabularyStudyState> {
  return http<VocabularyStudyState>(`/vocabulary/lesson/${lessonNumber}/answers`, {
    method: 'POST', body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer, request_id: requestId }),
  })
}

export function nextVocabularyQuestion(sessionId: string, lessonNumber = 1): Promise<VocabularyStudyState> {
  return http<VocabularyStudyState>(`/vocabulary/lesson/${lessonNumber}/next`, {
    method: 'POST', body: JSON.stringify({ session_id: sessionId }),
  })
}
