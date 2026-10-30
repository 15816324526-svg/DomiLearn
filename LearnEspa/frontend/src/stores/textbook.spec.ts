import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTextbookStore } from './textbook'
import type { TextbookState } from '@/types'

const api = vi.hoisted(() => ({
  getTextbookState: vi.fn(),
  uploadTextbook: vi.fn(),
  confirmTextbookImport: vi.fn(),
  retryTextbookImport: vi.fn(),
}))

vi.mock('@/api', () => api)

const queued: TextbookState = {
  id: 'modern-spanish-1',
  title: '现代西班牙语1',
  currentVersion: null,
  latestJob: {
    id: 'job-1',
    status: 'queued',
    displayFilename: '教材.pdf',
    totalPages: 305,
    processedPages: null,
    elapsedSeconds: 0,
    createdAt: '2026-10-26T00:00:00Z',
    startedAt: null,
    finishedAt: null,
    errorCode: null,
    errorMessage: null,
  },
}

describe('textbook store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    Object.values(api).forEach((mock) => mock.mockReset())
  })

  it('uploads immediately, reloads server state, and schedules active polling', async () => {
    api.uploadTextbook.mockResolvedValue(queued.latestJob)
    api.getTextbookState.mockResolvedValue(queued)
    const store = useTextbookStore()
    const file = new File(['pdf'], '教材.pdf', { type: 'application/pdf' })

    await store.upload(file)

    expect(api.uploadTextbook).toHaveBeenCalledWith(file)
    expect(store.latestJob?.status).toBe('queued')
    expect(vi.getTimerCount()).toBe(1)
    store.stopPolling()
  })

  it('keeps the last reliable state after a transient polling failure', async () => {
    api.getTextbookState.mockResolvedValueOnce(queued).mockRejectedValueOnce(new Error('后端离线'))
    const store = useTextbookStore()
    await store.load()
    store.startPolling()

    await vi.advanceTimersByTimeAsync(3000)

    expect(store.latestJob?.id).toBe('job-1')
    expect(store.connectionError).toBe('后端离线')
    expect(vi.getTimerCount()).toBe(1)
    store.stopPolling()
  })

  it('does not poll after a terminal state', async () => {
    api.getTextbookState.mockResolvedValue({
      ...queued,
      latestJob: { ...queued.latestJob!, status: 'failed' },
    })
    const store = useTextbookStore()
    await store.load()
    store.startPolling()

    expect(vi.getTimerCount()).toBe(0)
  })
})
