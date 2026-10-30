import { afterEach, describe, expect, it, vi } from 'vitest'
import { http } from './request'

describe('http', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lets the browser set the multipart boundary for FormData', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: 0, message: 'ok', data: { id: 'job-1' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const body = new FormData()
    body.append('file', new File(['pdf'], 'book.pdf', { type: 'application/pdf' }))
    await http('/upload', { method: 'POST', body })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(new Headers(init.headers).has('Content-Type')).toBe(false)
  })

  it('sets JSON content type for JSON request bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: 0, message: 'ok', data: {} }), { status: 200 })
    )
    vi.stubGlobal('fetch', fetchMock)

    await http('/json', { method: 'POST', body: JSON.stringify({ ok: true }) })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })
})
