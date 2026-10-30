import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useVocabularyStore } from './vocabulary'
import type { VocabularyStudyState } from '@/types'

const api = vi.hoisted(() => ({
  getVocabularyStudy: vi.fn(),
  submitVocabularyAnswer: vi.fn(),
  nextVocabularyQuestion: vi.fn(),
}))

vi.mock('@/api', () => api)

const starting: VocabularyStudyState = {
  overview: { title: '第一课', description: '背词', wordCount: 2, estimatedMinutes: 10 },
  session: {
    id: 'session-1', stage: 'choice', total: 2, done: 0, errors: 0,
    question: { id: 'word-1', lemma: 'hola', options: ['你好', '再见'] },
    feedback: null, summary: null,
  },
}

describe('vocabulary store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    Object.values(api).forEach((mock) => mock.mockReset())
    vi.stubGlobal('crypto', { randomUUID: () => 'request-1' })
  })

  it('shows saved feedback until explicit next and resumes it on reload', async () => {
    const answered: VocabularyStudyState = {
      ...starting,
      session: {
        ...starting.session, errors: 1,
        feedback: { correct: false, skipped: true, submittedAnswer: null, correctAnswer: '你好', correctOptionIndex: 0 },
      },
    }
    const nextState: VocabularyStudyState = {
      ...starting,
      session: { ...starting.session, question: { id: 'word-2', lemma: 'día', options: ['天', '你好'] } },
    }
    api.getVocabularyStudy.mockResolvedValueOnce(starting).mockResolvedValueOnce(answered)
    api.submitVocabularyAnswer.mockResolvedValue(answered)
    api.nextVocabularyQuestion.mockResolvedValue(nextState)
    const store = useVocabularyStore()

    await store.load()
    await store.submit(null)
    expect(api.submitVocabularyAnswer).toHaveBeenCalledWith('session-1', 'word-1', null, 'request-1', 1)
    expect(store.state?.session.feedback?.correctAnswer).toBe('你好')
    expect(api.nextVocabularyQuestion).not.toHaveBeenCalled()

    await store.load()
    expect(store.state?.session.feedback?.correctAnswer).toBe('你好')
    await store.next()
    expect(store.state?.session.question?.id).toBe('word-2')
    expect(store.state?.session.feedback).toBeNull()
  })

  it('shows backend errors instead of the demo word list', async () => {
    api.getVocabularyStudy.mockRejectedValue(new Error('请先在教材目录确认解析成功的教材'))
    const store = useVocabularyStore()
    await store.load()
    expect(store.state).toBeNull()
    expect(store.error).toContain('请先在教材目录确认')
  })

  it('keeps the selected chapter through a new store instance', async () => {
    api.getVocabularyStudy.mockResolvedValue(starting)
    const store = useVocabularyStore()
    await store.load(2)
    expect(api.getVocabularyStudy).toHaveBeenCalledWith(2)
    setActivePinia(createPinia())
    const resumed = useVocabularyStore()
    expect(resumed.lessonNumber).toBe(2)
    await resumed.load()
    expect(api.getVocabularyStudy).toHaveBeenLastCalledWith(2)
  })
})
