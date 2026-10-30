export type SourceMode = 'normal' | 'masked' | 'hidden'

export interface ModelSettings {
  model_id: string
  url: string
  has_api_key: boolean
}

export interface ImitationPassage {
  id: string
  lesson_number: number
  title: string
  source_text: string
  ready: boolean
  issue: string | null
  active_round_id: string | null
  sentence_count: number
}

export interface ImitationFeedback {
  verdict: 'rejected' | 'passed' | 'alternative' | 'manual'
  meaning_ok?: boolean
  grammar_ok?: boolean
  pattern_used?: boolean
  pattern_attempted?: boolean
  explanation: string
  revision?: string | null
}

export interface ImitationAttempt {
  id: string
  request_id: string
  answer: string
  status: 'pending' | 'complete' | 'manual'
  feedback: ImitationFeedback | null
  source_mode: SourceMode
  hint_viewed: boolean
  created_at: string
}

export interface ImitationRound {
  id: string
  passage_id: string
  status: 'active' | 'completed'
  title: string
  lesson_number: number
  source_text: string
  source_highlights: string[]
  background: string
  current_index: number
  total: number
  current_sentence: { id: string; speaker: string | null; chinese_text: string; hint: string | null } | null
  draft: string
  feedback: ImitationFeedback | null
  rejection_count: number
  can_next: boolean
  can_manual_pass: boolean
  attempts: ImitationAttempt[]
  default_source_mode: SourceMode
}

export interface ImitationHistory {
  id: string
  passage_id: string
  title: string
  lesson_number: number
  version_id: string
  created_at: string
  completed_at: string | null
  status: 'active' | 'completed'
  completed_count: number
  total: number
}

export interface ImitationReport {
  status: 'pending' | 'ready' | 'failed'
  memory_status: 'ready' | 'pending'
  summary: string | null
  counts: { first_pass: number; revised: number; alternative: number; manual_pass: number }
  used_patterns: string[]
  unobserved_patterns: string[]
  weak_patterns: string[]
  recurring_issues: string[]
  comparison: string | null
  next_suggestions: string[]
  attempts_by_sentence: Array<{
    sentence_id: string
    speaker: string | null
    chinese_text: string
    expected_pattern: string
    attempts: ImitationAttempt[]
  }>
  error: string | null
  model_usage: { input_tokens: number; output_tokens: number; total_tokens: number; calls: number }
}
