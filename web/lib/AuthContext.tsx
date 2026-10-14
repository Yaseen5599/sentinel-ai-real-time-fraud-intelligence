'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import {
  AuthenticatedUser,
  getStoredToken,
  loginAnalyst,
  clearStoredAuth,
  verifyCurrentSession
} from './supabaseClient'

interface AuthContextType {
  currentUser: AuthenticatedUser | null
  authToken: string | null
  isLoading: boolean
  login: (email: string, password?: string) => Promise<AuthenticatedUser>
  logout: () => void
  quickLogin: (preset: 'admin' | 'investigator' | 'customer') => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null)
  const [authToken, setAuthToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const initAuth = useCallback(async () => {
    setIsLoading(true)
    try {
      const stored = getStoredToken()
      if (stored) {
        setAuthToken(stored)
        const verified = await verifyCurrentSession()
        if (verified) {
          setCurrentUser(verified)
          setIsLoading(false)
          return
        }
      }

      // Default initial session using real credentials
      const res = await loginAnalyst('analyst.sarah@sentinel.ai', 'SentinelSecure2026!')
      setAuthToken(res.token)
      setCurrentUser(res.user)
    } catch (err) {
      console.warn('Initial session initialization:', err)
      // If backend is offline, leave user as null
      setCurrentUser(null)
      setAuthToken(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    initAuth()
  }, [initAuth])

  const login = async (email: string, password: string = 'SentinelSecure2026!'): Promise<AuthenticatedUser> => {
    setIsLoading(true)
    try {
      const res = await loginAnalyst(email, password)
      if (!res.user || !res.user.role || res.user.role === 'unassigned') {
        clearStoredAuth()
        setCurrentUser(null)
        setAuthToken(null)
        throw new Error('Access denied: Account has an unassigned or invalid role. Please contact an administrator.')
      }
      setAuthToken(res.token)
      setCurrentUser(res.user)
      return res.user
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    clearStoredAuth()
    setCurrentUser(null)
    setAuthToken(null)
  }

  // Pre-configured testing accounts that authenticate with REAL credentials (never client-side bypass)
  const quickLogin = async (preset: 'admin' | 'investigator' | 'customer') => {
    const creds = {
      admin: { email: 'admin.security@sentinel.ai', pass: 'SentinelSecure2026!' },
      investigator: { email: 'analyst.sarah@sentinel.ai', pass: 'SentinelSecure2026!' },
      customer: { email: 'customer.card007@sentinel.ai', pass: 'SentinelSecure2026!' }
    }
    const target = creds[preset]
    await login(target.email, target.pass)
  }

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        authToken,
        isLoading,
        login,
        logout,
        quickLogin
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
