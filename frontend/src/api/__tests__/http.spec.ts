import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, request, setUnauthorizedHandler } from '../http'

type FetchMock = (url: string, init?: RequestInit) => Promise<unknown>

function jsonResponse(status: number, body?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined) throw new Error('no body')
      return body
    },
  }
}

function headersOf(call: unknown[]): Record<string, string> {
  return (call[1] as { headers: Record<string, string> }).headers
}

describe('request', () => {
  beforeEach(() => {
    document.cookie = 'csrftoken=abc123'
  })

  afterEach(() => {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    setUnauthorizedHandler(null)
    vi.unstubAllGlobals()
  })

  it('sends the CSRF token on unsafe methods', async () => {
    const fetchMock = vi.fn<FetchMock>().mockResolvedValue(jsonResponse(204))
    vi.stubGlobal('fetch', fetchMock)

    await request('/api/thing/', { method: 'POST', body: { a: 1 } })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(headersOf(fetchMock.mock.calls[0]!)['X-CSRFToken']).toBe('abc123')
  })

  it('does not send the CSRF token on GET', async () => {
    const fetchMock = vi.fn<FetchMock>().mockResolvedValue(jsonResponse(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const body = await request<{ ok: boolean }>('/api/thing/')

    expect(body).toEqual({ ok: true })
    expect(headersOf(fetchMock.mock.calls[0]!)).not.toHaveProperty('X-CSRFToken')
  })

  it('fetches the CSRF cookie first when it is missing', async () => {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    const fetchMock = vi.fn<FetchMock>().mockImplementation(async (url: string) => {
      if (url === '/api/auth/csrf/') document.cookie = 'csrftoken=fresh'
      return jsonResponse(204)
    })
    vi.stubGlobal('fetch', fetchMock)

    await request('/api/thing/', { method: 'POST' })

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual(['/api/auth/csrf/', '/api/thing/'])
    expect(headersOf(fetchMock.mock.calls[1]!)['X-CSRFToken']).toBe('fresh')
  })

  it('throws an ApiError carrying the status and the field errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<FetchMock>().mockResolvedValue(
        jsonResponse(400, {
          new_password: ['Trop court.', 'Trop courant.'],
          non_field_errors: ['Formulaire invalide.'],
        }),
      ),
    )

    const error = await request('/api/thing/', { method: 'POST' }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    const apiError = error as ApiError
    expect(apiError.status).toBe(400)
    expect(apiError.message).toBe('Formulaire invalide.')
    expect(apiError.fieldErrors).toEqual({ new_password: ['Trop court.', 'Trop courant.'] })
  })

  it('calls the unauthorised handler on 401', async () => {
    const handler = vi.fn<() => void>()
    setUnauthorizedHandler(handler)
    vi.stubGlobal('fetch', vi.fn<FetchMock>().mockResolvedValue(jsonResponse(401, { detail: 'x' })))

    await expect(request('/api/thing/')).rejects.toMatchObject({ status: 401 })

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('stays quiet on 401 when asked to', async () => {
    const handler = vi.fn<() => void>()
    setUnauthorizedHandler(handler)
    vi.stubGlobal('fetch', vi.fn<FetchMock>().mockResolvedValue(jsonResponse(401, { detail: 'x' })))

    await expect(request('/api/thing/', { notifyUnauthorized: false })).rejects.toBeInstanceOf(
      ApiError,
    )

    expect(handler).not.toHaveBeenCalled()
  })
})
