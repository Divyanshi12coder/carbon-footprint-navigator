/**
 * Thin fetch wrapper: base URL from VITE_API_URL, bearer token injection, typed errors,
 * and a global "session expired" signal on 401 so the app can sign the user out cleanly.
 */

const RAW_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
export const API_BASE = `${RAW_BASE.replace(/\/$/, '')}/api`
const TOKEN_KEY = 'cfn.token'

export class ApiError extends Error {
  status: number
  details: unknown

  constructor(status: number, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.details = details
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token)
    } catch {
      /* storage unavailable (private mode) — session lasts for this tab only */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* ignore */
    }
  },
}

export const SESSION_EXPIRED_EVENT = 'cfn:session-expired'

interface ValidationIssue {
  loc?: (string | number)[]
  msg?: string
}

function messageFrom(status: number, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // FastAPI/Pydantic validation errors
      return (detail as ValidationIssue[])
        .map((d) => {
          const field = d.loc?.filter((p) => p !== 'body').join('.')
          const msg = (d.msg ?? 'Invalid value').replace(/^Value error, /, '')
          return field ? `${field}: ${msg}` : msg
        })
        .join(' · ')
    }
  }
  if (status === 0) return 'Cannot reach the server. Check your connection and try again.'
  if (status >= 500) return 'The server ran into a problem. Please try again.'
  return `Request failed (${status})`
}

export async function api<T>(path: string, init: RequestInit & { auth?: boolean } = {}): Promise<T> {
  const { auth = true, headers, ...rest } = init
  const h = new Headers(headers)
  if (rest.body && !h.has('Content-Type')) h.set('Content-Type', 'application/json')
  const token = tokenStore.get()
  if (auth && token) h.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...rest, headers: h })
  } catch {
    throw new ApiError(0, messageFrom(0, null))
  }

  if (response.status === 204) return undefined as T
  const text = await response.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!response.ok) {
    if (response.status === 401 && auth && token) {
      tokenStore.clear()
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, { detail: messageFrom(401, body) }))
    }
    throw new ApiError(response.status, messageFrom(response.status, body), body)
  }
  return body as T
}

export const json = (data: unknown) => JSON.stringify(data)
