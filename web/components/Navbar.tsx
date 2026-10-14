'use client'

import React, { useState, useEffect } from 'react'
import { ShieldAlert, Activity, Cpu, UserCheck, Terminal, Database, AlertTriangle } from 'lucide-react'

import { AuthenticatedUser } from '../lib/supabaseClient'
import { getRuntimeEnvironment } from '../lib/env'

interface StorageStatus {
  is_database_connected: boolean
  storage_mode: string
  backend: string
  survives_restart: boolean
  warning?: string | null
}

interface NavbarProps {
  latency: number
  isProcessing: boolean
  activeTab: 'stream' | 'cases' | 'architecture'
  setActiveTab: (tab: 'stream' | 'cases' | 'architecture') => void
  openCaseCount: number
  storageStatus?: StorageStatus | null
  currentUser?: AuthenticatedUser | null
  onOpenAuthModal?: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  latency,
  isProcessing,
  activeTab,
  setActiveTab,
  openCaseCount,
  storageStatus,
  currentUser,
  onOpenAuthModal
}) => {
  const isDbConnected = storageStatus?.is_database_connected ?? false
  const [envBadge, setEnvBadge] = useState<{ name: string; isProd: boolean }>({ name: 'LOCAL', isProd: false })

  useEffect(() => {
    setEnvBadge(getRuntimeEnvironment())
  }, [])

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-0.5 shadow-glow-primary flex items-center justify-center">
            <div className="h-full w-full bg-[#090D16] rounded-[10px] flex items-center justify-center">
              <ShieldAlert className="h-5 w-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-tight text-white text-lg">SENTINEL AI</span>
              <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full border font-mono ${
                envBadge.isProd
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              }`}>
                v1.0 {envBadge.name}
              </span>
            </div>
            <p className="text-xs text-slate-400">Real-Time Financial Fraud Intelligence</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('stream')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === 'stream'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            Live Stream
          </button>
          <button
            onClick={() => setActiveTab('cases')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === 'cases'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <UserCheck className="h-3.5 w-3.5" />
            Case Triage
            {openCaseCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-red-500 text-white font-bold">
                {openCaseCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('architecture')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === 'architecture'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            Model Pipeline
          </button>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-3">
          {/* Storage Tier Indicator */}
          <div
            title={storageStatus?.warning || 'Persistent PostgreSQL / Supabase Connected'}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs ${
              isDbConnected
                ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
                : 'bg-amber-950/30 border-amber-800/40 text-amber-300'
            }`}
          >
            {isDbConnected ? (
              <Database className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            )}
            <span className="font-medium text-slate-400">Storage:</span>
            <span className="font-semibold">
              {isDbConnected ? 'PostgreSQL' : 'RAM Buffer'}
            </span>
          </div>

          {/* Engine Latency */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <span className={`h-2 w-2 rounded-full ${isProcessing ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400'}`} />
            <span className="text-slate-400">Engine:</span>
            <span className="font-mono text-slate-200 font-semibold">{latency > 0 ? `${latency}ms` : '<15ms'}</span>
          </div>

          {/* Supabase Analyst Auth */}
          <button
            onClick={onOpenAuthModal}
            title={currentUser ? `Authenticated as ${currentUser.email} (${currentUser.role})` : 'Click to Sign In with Supabase JWT'}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
              currentUser
                ? 'bg-indigo-950/40 border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/40 shadow-sm'
                : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-indigo-500/60 hover:text-white'
            }`}
          >
            <Terminal className={`h-3.5 w-3.5 ${currentUser ? 'text-indigo-400' : 'text-slate-400'}`} />
            <span className="text-slate-400 font-medium">Auth:</span>
            <span className={`font-semibold ${currentUser ? 'text-indigo-200' : 'text-slate-200'}`}>
              {currentUser ? currentUser.name : 'Sign In'}
            </span>
            {currentUser && (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            )}
          </button>
        </div>
      </div>
    </header>
  )
}
