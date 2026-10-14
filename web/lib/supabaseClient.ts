import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://ixrwbfvsoqkxzmnfsuuq.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Export Supabase Client instance if anon key is configured
export const supabase: SupabaseClient | null = supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null

export interface AuthenticatedUser {
  id: string
  email: string
  name: string
  role: string
}

const TOKEN_KEY = 'sentinel_analyst_token'
const USER_KEY = 'sentinel_analyst_user'

export const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export const getStoredUser = (): AuthenticatedUser | null => {
  if (typeof window === 'undefined') return null
  const stored = localStorage.getItem(USER_KEY)
  if (!stored) return null
  try {
    return JSON.parse(stored) as AuthenticatedUser
  } catch {
    return null
  }
}

export const setStoredAuth = (token: string, user: AuthenticatedUser) => {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const clearStoredAuth = () => {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export const loginAnalyst = async (
  email: string,
  password: string = 'SentinelSecure2026!'
): Promise<{ token: string; user: AuthenticatedUser }> => {
  // 1. If Supabase Client is configured with anon key, authenticate directly through Supabase Auth
  if (supabase) {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
      })
      if (!error && data.session && data.user) {
        const token = data.session.access_token
        const appMeta = data.user.app_metadata || {}
        const userMeta = data.user.user_metadata || {}
        const user: AuthenticatedUser = {
          id: data.user.id,
          email: data.user.email || email,
          name: userMeta.full_name || email.split('@')[0].replace('.', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
          role: appMeta.role || 'unassigned'
        }
        setStoredAuth(token, user)
        return { token, user }
      }
    } catch {
      // Fallback to gateway auth below
    }
  }

  // 2. Gateway authentication: verify credentials against trusted store (never client-supplied role)
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  const res = await fetch(`${apiBase}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Authentication failed. Please check credentials.')
  }

  const data = await res.json()
  setStoredAuth(data.access_token, data.user)
  return { token: data.access_token, user: data.user }
}

export const verifyCurrentSession = async (): Promise<AuthenticatedUser | null> => {
  const token = getStoredToken()
  if (!token) return null

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  try {
    const res = await fetch(`${apiBase}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) {
      clearStoredAuth()
      return null
    }
    const data = await res.json()
    const verifiedRole = data.role && data.role !== 'unassigned' ? data.role : 'unassigned'
    const verifiedUser: AuthenticatedUser = {
      id: data.user_id,
      email: data.email,
      name: data.email.split('@')[0].replace('.', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
      role: verifiedRole
    }
    setStoredAuth(token, verifiedUser)
    return verifiedUser
  } catch {
    // Fail closed: never trust unverified or stale cached roles in localStorage as proof of authorization
    clearStoredAuth()
    return null
  }
}
