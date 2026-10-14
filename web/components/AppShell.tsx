'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  ShieldAlert,
  LayoutDashboard,
  CreditCard,
  UserCheck,
  Cpu,
  Activity,
  Users,
  AlertTriangle,
  History,
  FileWarning,
  LogIn,
  LogOut,
  ChevronDown,
  Menu,
  X,
  Database,
  Radio,
  CheckCircle2,
  Clock,
  ExternalLink
} from 'lucide-react'
import { useAuth } from '../lib/AuthContext'
import { api } from '../lib/api'
import { getRuntimeEnvironment } from '../lib/env'

interface AppShellProps {
  children: React.ReactNode
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  title,
  subtitle,
  actions
}) => {
  const pathname = usePathname()
  const router = useRouter()
  const { currentUser, authToken, logout, isLoading } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [storageStatus, setStorageStatus] = useState<any>({
    is_database_connected: false,
    storage_mode: 'in_memory_buffer',
    backend: 'Loading...'
  })
  const [engineLatency, setEngineLatency] = useState<number | null>(null)
  const [envBadge, setEnvBadge] = useState<{ name: string; isProd: boolean }>({ name: 'LOCAL', isProd: false })

  useEffect(() => {
    setEnvBadge(getRuntimeEnvironment())
  }, [])

  // Fetch live storage health and latency
  useEffect(() => {
    let isMounted = true
    const fetchStatus = async () => {
      try {
        const data = await api.get('/api/v1/storage/status')
        if (isMounted && data) {
          setStorageStatus(data)
        }
      } catch {
        // Offline backend graceful fallback
      }

      try {
        const kData = await api.get('/api/v1/analytics/kpis')
        if (isMounted && kData?.avg_latency_ms) {
          setEngineLatency(kData.avg_latency_ms)
        }
      } catch {
        // Unauthenticated or unprivileged fallback
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [])

  const role = currentUser?.role || 'guest'

  // Navigation schema configured by role
  const adminNav = [
    { label: 'Authority Console', href: '/', icon: LayoutDashboard },
    { label: 'Transaction Explorer', href: '/transactions', icon: CreditCard },
    { label: 'Investigation Workspace', href: '/investigations', icon: UserCheck },
    { label: 'Model Intelligence', href: '/analytics', icon: Cpu },
    { label: 'Pipeline Monitoring', href: '/pipeline', icon: Activity },
    { label: 'User & Access RBAC', href: '/admin/users', icon: Users },
  ]

  const investigatorNav = [
    { label: 'Authority Console', href: '/', icon: LayoutDashboard },
    { label: 'Transaction Explorer', href: '/transactions', icon: CreditCard },
    { label: 'Investigation Workspace', href: '/investigations', icon: UserCheck },
    { label: 'Model Intelligence', href: '/analytics', icon: Cpu },
  ]

  const customerNav = [
    { label: 'Customer Dashboard', href: '/customer', icon: LayoutDashboard },
    { label: 'Authorized Transactions', href: '/customer/transactions', icon: History },
    { label: 'Report Suspicious Activity', href: '/customer/report', icon: FileWarning },
  ]

  const guestNav = [
    { label: 'Platform Overview', href: '/', icon: LayoutDashboard },
    { label: 'Customer Portal', href: '/customer', icon: CreditCard },
    { label: 'Sign In', href: '/login', icon: LogIn },
  ]

  const navLinks = !currentUser
    ? guestNav
    : role === 'admin'
    ? adminNav
    : role === 'customer'
    ? customerNav
    : investigatorNav


  return (
    <div className="min-h-screen flex bg-canvas">
      {/* ----------------- Midnight-Navy Sidebar ----------------- */}
      <aside className="hidden md:flex flex-col w-64 bg-sidebar border-r border-sidebar-border select-none z-30 shrink-0">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-5 border-b border-sidebar-border gap-3">
          <div className="h-9 w-9 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-sm shadow-brand-500/30">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm tracking-wide text-white">SENTINEL AI</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded border font-mono ${
                envBadge.isProd
                  ? 'bg-rose-500/20 text-rose-200 border-rose-500/40'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              }`}>
                {envBadge.name}
              </span>
            </div>
            <p className="text-[11px] text-sidebar-ink-muted">Fraud Intelligence</p>
          </div>
        </div>

        {/* Current Role Banner */}
        <div className="px-4 py-3 border-b border-sidebar-border bg-[#070B14]">
          <div className="flex items-center justify-between text-[11px] mb-1">
            <span className="text-sidebar-ink-muted uppercase font-semibold tracking-wider text-[10px]">
              Active Identity
            </span>
            <span
              className={`px-1.5 py-0.5 rounded font-mono font-semibold text-[10px] uppercase ${
                role === 'admin'
                  ? 'bg-purple-950 text-purple-300 border border-purple-800'
                  : role === 'customer'
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-blue-950 text-blue-300 border border-blue-800'
              }`}
            >
              {role.replace('_', ' ')}
            </span>
          </div>
          <p className="text-xs font-medium text-sidebar-ink truncate">
            {currentUser?.name || 'Unassigned Session'}
          </p>
          <p className="text-[11px] text-sidebar-ink-muted truncate font-mono">
            {currentUser?.email || 'Offline'}
          </p>
        </div>

        {/* Navigation Section */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] font-bold text-sidebar-ink-muted uppercase tracking-wider">
            {role === 'customer' ? 'Customer Portal' : 'Authority Navigation'}
          </div>
          {navLinks.map(link => {
            const Icon = link.icon
            const isActive = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-sidebar-ink-muted hover:text-white hover:bg-sidebar-hover'
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{link.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-sidebar-border flex items-center justify-between">
          <Link
            href="/login"
            className="flex items-center gap-2 text-xs text-sidebar-ink-muted hover:text-white transition-colors"
          >
            <LogIn className="h-3.5 w-3.5" />
            <span>Login Portal</span>
          </Link>
          {currentUser && (
            <button
              onClick={logout}
              title="Sign Out"
              className="p-1 rounded text-sidebar-ink-muted hover:text-rose-400 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </aside>

      {/* ----------------- Main Layout Body ----------------- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-surface border-b border-surface-border flex items-center justify-between px-6 sticky top-0 z-20 shadow-sm">
          <div className="flex items-center gap-3">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-ink hover:bg-surface-subtle"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <div>
              <h1 className="text-base font-bold text-ink tracking-tight">{title}</h1>
              {subtitle && <p className="text-xs text-ink-muted">{subtitle}</p>}
            </div>
          </div>

          {/* Right Header Status Badges */}
          <div className="flex items-center gap-3">
            {/* Live Latency Telemetry */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-subtle border border-surface-border text-xs text-ink-secondary">
              <Clock className="h-3.5 w-3.5 text-brand-600" />
              <span className="font-mono tabular-nums font-semibold">
                {engineLatency !== null ? `${engineLatency.toFixed(1)} ms` : '-- ms'}
              </span>
              <span className="text-[10px] text-ink-muted">latency</span>
            </div>

            {/* Storage Tier Indicator */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                storageStatus.is_database_connected
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              <Database className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden md:inline">
                {storageStatus.is_database_connected ? 'PostgreSQL Active' : 'Ephemeral Buffer Mode'}
              </span>
              <span className="md:hidden">
                {storageStatus.is_database_connected ? 'DB' : 'RAM'}
              </span>
            </div>

            {/* Action Slot */}
            {actions && <div className="flex items-center gap-2">{actions}</div>}
          </div>
        </header>

        {/* Mobile Nav Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-sidebar text-white p-4 border-b border-sidebar-border z-30">
            <nav className="space-y-1">
              {navLinks.map(link => {
                const Icon = link.icon
                const isActive = pathname === link.href
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                      isActive ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-sidebar-hover'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{link.label}</span>
                  </Link>
                )
              })}
            </nav>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-surface-border py-4 px-6 text-center text-xs text-ink-muted bg-surface">
          <p>
            Sentinel AI — Adaptive Real-Time Financial Fraud Intelligence Platform · Big Data Analytics · Local Development
          </p>
        </footer>
      </div>
    </div>
  )
}
