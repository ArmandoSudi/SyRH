/**
 * The one place that talks to the API.
 *
 * Sends the CSRF token on unsafe methods, parses JSON, and turns every failure
 * into an ApiError that carries the HTTP status and DRF's per-field messages.
 */

export type FieldErrors = Record<string, string[]>

export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: FieldErrors

  constructor(status: number, message: string, fieldErrors: FieldErrors = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  /** Set to false when a 401 is an expected answer, not an expired session. */
  notifyUnauthorized?: boolean
}

const CSRF_COOKIE = 'csrftoken'
const CSRF_URL = '/api/auth/csrf/'

let unauthorizedHandler: (() => void) | null = null

/** Registers what happens when the session turns out to be gone (HTTP 401). */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`
  const entry = document.cookie.split('; ').find((part) => part.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null
}

async function csrfToken(): Promise<string> {
  // Django only sets the cookie once asked, so the first unsafe call fetches it.
  if (!readCookie(CSRF_COOKIE)) {
    await fetch(CSRF_URL, { credentials: 'same-origin' })
  }
  return readCookie(CSRF_COOKIE) ?? ''
}

function asMessages(value: unknown): string[] {
  return (Array.isArray(value) ? value : [value]).map(String)
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `API responded with HTTP ${response.status}`
  const fieldErrors: FieldErrors = {}
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && !Array.isArray(body)) {
      for (const [key, value] of Object.entries(body)) {
        if (key === 'detail' || key === 'non_field_errors') {
          message = asMessages(value)[0] ?? message
        } else {
          fieldErrors[key] = asMessages(value)
        }
      }
    }
  } catch {
    // Not JSON (proxy error page, empty body): keep the generic message.
  }
  return new ApiError(response.status, message, fieldErrors)
}

export async function request<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, notifyUnauthorized = true } = options
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (method !== 'GET') {
    headers['X-CSRFToken'] = await csrfToken()
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })

  if (!response.ok) {
    if (response.status === 401 && notifyUnauthorized) {
      unauthorizedHandler?.()
    }
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json()
}
