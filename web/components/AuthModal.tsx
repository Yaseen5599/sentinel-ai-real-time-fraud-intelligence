'use client'

import React, { useState } from 'react'
import { ShieldCheck, Lock, Mail, Key, X, AlertCircle, CheckCircle2, User, Sparkles } from 'lucide-react'
import { AuthenticatedUser, loginAnalyst } from '../lib/supabaseClient'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  currentUser: AuthenticatedUser | null
  onAuthSuccess: (user: AuthenticatedUser, token: string) => void
  onSignOut: () => void
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onAuthSuccess,
  onSignOut
}) => {
  const [email, setEmail] = useState('analyst.sarah@sentinel.ai')
  const [password, setPassword] = useState('SentinelSecure2026!')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleLogin = async (loginEmail?: string) => {
    setIsLoading(true)
    setError(null)
    const targetEmail = loginEmail || email

    try {
      const res = await loginAnalyst(targetEmail, password)
      onAuthSuccess(res.user, res.token)
      onClose()
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-md rounded-2xl glass-card border border-indigo-500/30 p-6 shadow-2xl shadow-indigo-950/50">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-glow-primary">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              Analyst Authentication
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Supabase JWT
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Cryptographically verified RBAC access for case triage
            </p>
          </div>
        </div>

        {currentUser ? (
          /* Active Session View */
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-emerald-500/30 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                Active Authenticated Session
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Analyst:</span>
                  <span className="text-white font-medium">{currentUser.name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Email:</span>
                  <span className="text-white font-mono">{currentUser.email}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">RBAC Role:</span>
                  <span className="text-indigo-400 font-semibold">{currentUser.role}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Audience / Issuer:</span>
                  <span className="text-slate-300 font-mono">authenticated</span>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  onSignOut()
                  onClose()
                }}
                className="flex-1 py-2.5 rounded-xl border border-red-500/40 bg-red-950/20 hover:bg-red-950/40 text-red-400 text-xs font-semibold transition-all"
              >
                Sign Out
              </button>
              <button
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-md shadow-indigo-600/30"
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          /* Login Form */
          <div className="space-y-4">
            {error && (
              <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Quick Demo Credentials */}
            <div className="p-3 rounded-xl bg-indigo-950/30 border border-indigo-500/20 space-y-2">
              <span className="text-[11px] font-semibold text-indigo-300 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3 text-indigo-400" /> Quick Analyst Sign-In (Pre-configured)
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleLogin('analyst.sarah@sentinel.ai')}
                  disabled={isLoading}
                  className="flex-1 py-1.5 px-2.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 text-[11px] text-indigo-200 font-medium transition-all text-left"
                >
                  <span className="block font-semibold">Sarah Connor</span>
                  <span className="text-[10px] text-slate-400">Lead Investigator</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleLogin('analyst.marcus@sentinel.ai')}
                  disabled={isLoading}
                  className="flex-1 py-1.5 px-2.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 text-[11px] text-indigo-200 font-medium transition-all text-left"
                >
                  <span className="block font-semibold">Marcus Wright</span>
                  <span className="text-[10px] text-slate-400">Senior Triage</span>
                </button>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleLogin()
              }}
              className="space-y-3"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Analyst Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                    placeholder="analyst@sentinel.ai"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Password / Credential
                </label>
                <div className="relative">
                  <Key className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isLoading ? (
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <ShieldCheck className="h-4 w-4" />
                    Authenticate Analyst Session
                  </>
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
