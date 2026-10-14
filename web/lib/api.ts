/**
 * Sentinel AI — Authenticated API Client
 *
 * Requirements:
 * - Attaches valid Bearer tokens to protected requests from trusted storage.
 * - Preserves public endpoint behavior when no token is present.
 * - Handles 401 (Unauthorized) and 403 (Forbidden) distinctly.
 * - Avoids unnecessary logout loops by avoiding aggressive uncoordinated redirect side effects.
 * - Does not create insecure authentication fallbacks.
 * - Provides consistent, structured error handling via ApiError.
 */

import { getStoredToken } from './supabaseClient'

export class ApiError extends Error {
  status: number
  detail: string
  data?: any

  constructor(status: number, detail: string, data?: any) {
    super(detail || `API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.data = data
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean
}

/**
 * Core fetch wrapper with cryptographic Bearer token injection and status validation.
 */
export async function apiFetch<T = any>(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const { skipAuth = false, headers: customHeaders, ...restOptions } = options

  // Construct absolute URL if path is relative
  const url = endpoint.startsWith('http://') || endpoint.startsWith('https://')
    ? endpoint
    : `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`

  const headers = new Headers(customHeaders || {})

  // Attach Content-Type if request has body and not already specified
  if (restOptions.body && !headers.has('Content-Type') && typeof restOptions.body === 'string') {
    headers.set('Content-Type', 'application/json')
  }

  // Attach Bearer token from verified storage if not explicitly skipped
  if (!skipAuth && !headers.has('Authorization')) {
    const token = getStoredToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const response = await fetch(url, {
    ...restOptions,
    headers
  })

  // Successful response handling
  if (response.ok) {
    if (response.status === 204) {
      return {} as T
    }
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      return (await response.json()) as T
    }
    return (await response.text()) as unknown as T
  }

  // Error parsing
  let errorData: any = null
  let detail = `Request failed with status ${response.status}`

  try {
    const text = await response.text()
    if (text) {
      try {
        errorData = JSON.parse(text)
        if (errorData?.detail) {
          detail = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail)
        } else if (errorData?.message) {
          detail = errorData.message
        }
      } catch {
        detail = text
      }
    }
  } catch {
    // Stream read failure fallback
  }

  // Specific status code semantics
  if (response.status === 401) {
    // 401: Token missing or expired.
    // NOTE: Avoid aggressive window.location redirect here to prevent infinite logout/login redirect loops.
    // Callers or AppShell handle displaying auth prompt gracefully.
    throw new ApiError(401, detail || 'Authentication required or session expired.', errorData)
  }

  if (response.status === 403) {
    // 403: Role forbidden. User IS authenticated, but lacks privilege for this action.
    // Never clear credentials or log out on 403.
    throw new ApiError(403, detail || 'Access forbidden: Insufficient role permissions.', errorData)
  }

  throw new ApiError(response.status, detail, errorData)
}

/**
 * Ergonomic HTTP convenience methods.
 */
export const api = {
  get: <T = any>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, body?: any, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined
    }),

  patch: <T = any>(endpoint: string, body?: any, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined
    }),

  put: <T = any>(endpoint: string, body?: any, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined
    }),

  delete: <T = any>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: 'DELETE' })
}
