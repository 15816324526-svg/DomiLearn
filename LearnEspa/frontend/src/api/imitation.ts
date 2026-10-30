import { http } from './request'
import type {
  ImitationHistory, ImitationPassage, ImitationReport, ImitationRound, ModelSettings, SourceMode,
} from '@/types/imitation'

export const getModelSettings = () => http<ModelSettings>('/model-settings')
export const testModelSettings = (fields: { model_id: string; url: string; api_key: string }) =>
  http<ModelSettings>('/model-settings/test', { method: 'POST', body: JSON.stringify(fields) })

export const listImitationPassages = () => http<ImitationPassage[]>('/imitation/passages')
export const startImitationRound = (passageId: string) =>
  http<ImitationRound>(`/imitation/passages/${passageId}/rounds`, { method: 'POST' })
export const getImitationRound = (roundId: string) => http<ImitationRound>(`/imitation/rounds/${roundId}`)
export const saveImitationDraft = (roundId: string, text: string) =>
  http<ImitationRound>(`/imitation/rounds/${roundId}/draft`, { method: 'PUT', body: JSON.stringify({ text }) })
export const submitImitationAnswer = (roundId: string, body: {
  request_id: string; answer: string; source_mode: SourceMode; hint_viewed: boolean
}) => http<ImitationRound>(`/imitation/rounds/${roundId}/answers`, { method: 'POST', body: JSON.stringify(body) })
export const advanceImitation = (roundId: string, manualPass = false) =>
  http<ImitationRound>(`/imitation/rounds/${roundId}/next`, {
    method: 'POST', body: JSON.stringify({ manual_pass: manualPass }),
  })
export const getImitationPreferences = () => http<{ default_source_mode: SourceMode }>('/imitation/preferences')
export const setImitationPreferences = (mode: SourceMode) =>
  http<{ default_source_mode: SourceMode }>('/imitation/preferences', {
    method: 'PUT', body: JSON.stringify({ default_source_mode: mode }),
  })
export const listImitationHistory = () => http<ImitationHistory[]>('/imitation/history')
export const getImitationReport = (roundId: string) => http<ImitationReport>(`/imitation/rounds/${roundId}/report`)
export const retryImitationReport = (roundId: string) =>
  http<ImitationReport>(`/imitation/rounds/${roundId}/report/retry`, { method: 'POST' })
