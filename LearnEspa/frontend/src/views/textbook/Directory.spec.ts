import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Directory from './Directory.vue'
import { useUiStore } from '@/stores/ui'
import type { TextbookState } from '@/types'

const api = vi.hoisted(() => ({
  getTextbookState: vi.fn(),
  uploadTextbook: vi.fn(),
  confirmTextbookImport: vi.fn(),
  retryTextbookImport: vi.fn(),
}))

vi.mock('@/api', () => api)

const emptyState: TextbookState = {
  id: 'modern-spanish-1',
  title: '现代西班牙语1',
  currentVersion: null,
  latestJob: null,
}

function mountPage(state: TextbookState) {
  api.getTextbookState.mockResolvedValue(state)
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(Directory, { global: { plugins: [pinia] } })
}

describe('教材目录页面', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Object.values(api).forEach((mock) => mock.mockReset())
  })

  it('shows the PDF drop zone when no textbook has been imported', async () => {
    const wrapper = mountPage(emptyState)
    await flushPromises()

    expect(wrapper.text()).toContain('将教材 PDF 拖到这里')
    expect(wrapper.find('input[type="file"]').attributes('accept')).toContain('.pdf')
  })

  it('starts upload immediately after a PDF is dropped', async () => {
    api.uploadTextbook.mockResolvedValue({ id: 'job-1' })
    const queued = {
      ...emptyState,
      latestJob: {
        id: 'job-1', status: 'queued', displayFilename: '改过名字.pdf', totalPages: 5,
        processedPages: null, elapsedSeconds: 0, createdAt: '2026-10-26T00:00:00Z',
        startedAt: null, finishedAt: null, errorCode: null, errorMessage: null,
      },
    } satisfies TextbookState
    api.getTextbookState.mockResolvedValueOnce(emptyState).mockResolvedValueOnce(queued)
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(Directory, { global: { plugins: [pinia] } })
    await flushPromises()

    const file = new File(['%PDF'], '改过名字.pdf', { type: 'application/pdf' })
    await wrapper.find('.textbook-dropzone').trigger('drop', {
      dataTransfer: { files: [file] },
    })
    await flushPromises()

    expect(api.uploadTextbook).toHaveBeenCalledWith(file)
    expect(wrapper.text()).toContain('正在解析教材')
    expect(wrapper.text()).toContain('改过名字.pdf')
  })

  it('rejects a non-PDF locally before calling the backend', async () => {
    const wrapper = mountPage(emptyState)
    await flushPromises()
    const file = new File(['text'], 'notes.txt', { type: 'text/plain' })

    await wrapper.find('.textbook-dropzone').trigger('drop', {
      dataTransfer: { files: [file] },
    })

    expect(api.uploadTextbook).not.toHaveBeenCalled()
    expect(useUiStore().message).toBe('请选择 PDF 文件')
  })

  it('shows confirm and retry actions for a successful conversion', async () => {
    const success = {
      ...emptyState,
      latestJob: {
        id: 'job-2', status: 'awaiting_confirmation', displayFilename: '教材.pdf', totalPages: 305,
        processedPages: 305, elapsedSeconds: 80, createdAt: '2026-10-26T00:00:00Z',
        startedAt: '2026-10-26T00:00:01Z', finishedAt: '2026-10-26T00:01:21Z',
        errorCode: null, errorMessage: null,
      },
    } satisfies TextbookState
    const wrapper = mountPage(success)
    await flushPromises()

    expect(wrapper.text()).toContain('教材解析成功')
    expect(wrapper.text()).toContain('确认使用')
    expect(wrapper.text()).toContain('重新解析')
  })
})
