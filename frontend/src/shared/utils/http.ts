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

/** An ApiError from a status and a parsed body (undefined when not JSON). */
function apiErrorFrom(status: number, body: unknown): ApiError {
  let message = `API responded with HTTP ${status}`
  const fieldErrors: FieldErrors = {}
  if (body && typeof body === 'object' && !Array.isArray(body)) {
    for (const [key, value] of Object.entries(body)) {
      if (key === 'detail' || key === 'non_field_errors') {
        message = asMessages(value)[0] ?? message
      } else {
        fieldErrors[key] = asMessages(value)
      }
    }
  }
  return new ApiError(status, message, fieldErrors)
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    // Not JSON (proxy error page, empty body): keep the generic message.
  }
  return apiErrorFrom(response.status, body)
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

/**
 * Sends a multipart form with upload progress (fetch reports none), with the same
 * CSRF token, ApiError and lost-session behaviour as request().
 * onProgress receives a fraction from 0 to 1.
 */
export async function upload<T>(
  path: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
): Promise<T> {
  const token = await csrfToken()
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', path)
    xhr.withCredentials = true
    xhr.setRequestHeader('Accept', 'application/json')
    xhr.setRequestHeader('X-CSRFToken', token)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total)
    }
    xhr.onerror = () => reject(new ApiError(0, "Le serveur n'a pas pu être joint."))
    xhr.onload = () => {
      let body: unknown
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : undefined
      } catch {
        body = undefined
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as T)
        return
      }
      if (xhr.status === 401) unauthorizedHandler?.()
      reject(apiErrorFrom(xhr.status, body))
    }
    xhr.send(form)
  })
}
