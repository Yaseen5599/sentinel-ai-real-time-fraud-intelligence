'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ShieldAlert,
  Lock,
  Mail,
  Key,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  User,
  ExternalLink
} from 'lucide-react'
import { useAuth } from '../../lib/AuthContext'

export default function LoginPage() {
  const router = useRouter()
  const { login, currentUser, logout } = useAuth()
  const [email, setEmail] = useState('analyst.sarah@sentinel.ai')
  const [password, setPassword] = useState('SentinelSecure2026!')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const verifiedUser = await login(email, password)
      setSuccess(true)
      setTimeout(() => {
        if (verifiedUser.role === 'customer') {
          router.push('/customer')
        } else if (verifiedUser.role === 'admin' || verifiedUser.role === 'fraud_investigator') {
          router.push('/')
        } else {
          setError('Access denied: Account has an unassigned or unauthorized role.')
        }
      }, 500)
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  const fillTestCredentials = (testEmail: string) => {
    setEmail(testEmail)
    setPassword('SentinelSecure2026!')
    setError(null)
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex h-12 w-12 rounded-xl bg-sidebar border border-sidebar-border items-center justify-center text-brand-500 shadow-sm mb-3">
          <ShieldAlert className="h-7 w-7 text-brand-500" />
        </div>
        <h2 className="text-2xl font-black tracking-tight text-ink">
          SENTINEL AI
        </h2>
        <p className="mt-1 text-xs text-ink-muted">
          Real-Time Financial Fraud Intelligence Platform · Authentication Gateway
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-surface py-8 px-6 shadow-card border border-surface-border rounded-2xl sm:px-10">
          {currentUser ? (
            <div className="space-y-4 text-center">
              <div className="inline-flex h-12 w-12 rounded-full bg-emerald-50 text-emerald-600 items-center justify-center mx-auto">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-ink">Active Session Verified</h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Logged in as <strong className="text-ink">{currentUser.name}</strong> ({currentUser.email})
                </p>
                <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-50 text-brand-700 border border-brand-200">
                  Role: {currentUser.role}
                </span>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={logout}
                  className="flex-1 py-2 px-4 rounded-lg border border-surface-border-strong text-xs font-semibold text-ink-secondary hover:bg-surface-subtle transition-all"
                >
                  Sign Out
                </button>
                <Link
                  href={currentUser.role === 'customer' ? '/customer' : '/'}
                  className="flex-1 py-2 px-4 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-sm"
                >
                  <span>Go to App</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Email Address
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-ink-muted">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="analyst.sarah@sentinel.ai"
                    className="block w-full pl-9 pr-3 py-2 text-xs border border-surface-border-strong rounded-lg text-ink placeholder-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Password
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-ink-muted">
                    <Key className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="block w-full pl-9 pr-3 py-2 text-xs border border-surface-border-strong rounded-lg text-ink placeholder-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 font-mono"
                  />
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>Authentication successful. Redirecting...</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 transition-all disabled:opacity-50"
              >
                {isLoading ? 'Authenticating with Supabase JWT...' : 'Sign In to Sentinel AI'}
              </button>
            </form>
          )}

          {/* Test Preset Accounts with Real Credential Verification */}
          <div className="mt-6 pt-6 border-t border-surface-border">
            <p className="text-[11px] font-bold text-ink-muted uppercase tracking-wider mb-2 text-center">
              Verified Test Accounts (Real Credentials)
            </p>
            <div className="space-y-1.5">
              <button
                type="button"
                onClick={() => fillTestCredentials('admin.security@sentinel.ai')}
                className="w-full text-left p-2 rounded-lg border border-surface-border hover:bg-surface-subtle transition-all flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-semibold text-ink block">admin.security@sentinel.ai</span>
                  <span className="text-[10px] text-ink-muted">Executive Security Administrator</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-bold border border-purple-200">
                  ADMIN
                </span>
              </button>

              <button
                type="button"
                onClick={() => fillTestCredentials('analyst.sarah@sentinel.ai')}
                className="w-full text-left p-2 rounded-lg border border-surface-border hover:bg-surface-subtle transition-all flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-semibold text-ink block">analyst.sarah@sentinel.ai</span>
                  <span className="text-[10px] text-ink-muted">Senior Fraud Investigator</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200">
                  INVESTIGATOR
                </span>
              </button>

              <button
                type="button"
                onClick={() => fillTestCredentials('customer.card007@sentinel.ai')}
                className="w-full text-left p-2 rounded-lg border border-surface-border hover:bg-surface-subtle transition-all flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-semibold text-ink block">customer.card007@sentinel.ai</span>
                  <span className="text-[10px] text-ink-muted">Cardholder (Card 007)</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                  CUSTOMER
                </span>
              </button>
            </div>
            <p className="text-[10px] text-ink-muted mt-3 text-center">
              All logins authenticate cryptographically via server JWT. Privilege escalation is strictly prevented.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
