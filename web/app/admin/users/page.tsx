'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Users,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Key,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  Clock,
  LogIn
} from 'lucide-react'
import { AppShell } from '../../../components/AppShell'
import { useAuth } from '../../../lib/AuthContext'
import { api } from '../../../lib/api'

export default function UserAccessManagementPage() {
  const { currentUser, authToken, quickLogin } = useAuth()
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [logError, setLogError] = useState<string | null>(null)
  const [users, setUsers] = useState<any[]>([])
  const [isLoadingUsers, setIsLoadingUsers] = useState(false)
  const [userSource, setUserSource] = useState<string>('trusted_registry')
  const [userError, setUserError] = useState<string | null>(null)

  const isAdmin = currentUser?.role === 'admin'

  useEffect(() => {
    if (!isAdmin || !authToken) return

    const fetchData = async () => {
      setIsLoadingUsers(true)
      setIsLoadingLogs(true)
      setUserError(null)
      setLogError(null)

      try {
        const userData = await api.get('/api/v1/admin/users')
        if (userData?.users) {
          setUsers(userData.users)
          setUserSource(userData.source || 'trusted_registry')
        }
      } catch (err: any) {
        setUserError(err.message || 'Unable to retrieve user records from trusted source.')
      } finally {
        setIsLoadingUsers(false)
      }

      try {
        const logData = await api.get('/api/v1/admin/audit-logs')
        setAuditLogs(logData.logs || (Array.isArray(logData) ? logData : []))
      } catch (err: any) {
        setLogError(err.message || 'Failed to fetch audit logs.')
      } finally {
        setIsLoadingLogs(false)
      }
    }

    fetchData()
  }, [isAdmin, authToken])

  // Permissions Matrix Definition
  const permissions = [
    { capability: 'View Telemetry & Live Scoring', admin: true, investigator: true, customer: false },
    { capability: 'Simulate Attack Scenarios', admin: true, investigator: true, customer: false },
    { capability: 'Review & Resolve Fraud Cases', admin: true, investigator: true, customer: false },
    { capability: 'Access Model Intelligence & Thresholds', admin: true, investigator: true, customer: false },
    { capability: 'Access Stream Pipeline Diagnostics', admin: true, investigator: false, customer: false },
    { capability: 'View Administrative Audit Logs', admin: true, investigator: false, customer: false },
    { capability: 'Inspect Own Card Transactions', admin: true, investigator: false, customer: true },
    { capability: 'Submit Suspicious Transaction Disputes', admin: false, investigator: false, customer: true }
  ]

  return (
    <AppShell
      title="User & Access Management (RBAC)"
      subtitle="Role-Based Security, Policy Governance & Audit Log Verification"
    >
      {/* Non-Admin Warning Banner */}
      {!isAdmin && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-amber-600 shrink-0" />
            <div className="text-xs">
              <strong>Admin Clearance Required:</strong> You are currently authenticated as{' '}
              <span className="font-semibold">{currentUser?.name || 'Guest'}</span> ({currentUser?.role || 'unassigned'}).
              Audit logs and role provisioning require an <span className="font-bold">admin</span> token.
            </div>
          </div>
          <button
            onClick={() => quickLogin('admin')}
            className="px-3 py-1.5 rounded-lg bg-purple-600 text-white font-semibold text-xs hover:bg-purple-700 transition-colors shrink-0 shadow-sm"
          >
            Authenticate as Admin
          </button>
        </div>
      )}

      {/* Provisioned Users Table */}
      <div className="bg-surface rounded-xl border border-surface-border shadow-card overflow-hidden">
        <div className="p-4 border-b border-surface-border flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-ink">Provisioned User Accounts</h3>
            <p className="text-xs text-ink-muted">Accounts managed via Supabase Auth & Gateway registry</p>
          </div>
          <span className="text-xs text-ink-muted font-mono">{users.length} verified accounts</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-canvas border-b border-surface-border text-ink-muted uppercase font-semibold text-[10px]">
              <tr>
                <th className="py-2.5 px-4">User</th>
                <th className="py-2.5 px-4">Email</th>
                <th className="py-2.5 px-4">Role</th>
                <th className="py-2.5 px-4">Department / Scope</th>
                <th className="py-2.5 px-4 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-surface-subtle transition-colors">
                  <td className="py-3 px-4 font-semibold text-ink">{u.name}</td>
                  <td className="py-3 px-4 font-mono text-ink-secondary">{u.email}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                        u.role === 'admin'
                          ? 'bg-purple-50 text-purple-700 border-purple-200'
                          : u.role === 'customer'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {u.role.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-ink-muted text-[11px]">{u.department}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {u.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-ink-muted text-[11px]">{u.lastLogin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Permissions Capability Matrix */}
      <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-card">
        <h3 className="text-sm font-bold text-ink mb-1">Role-Based Permission Governance</h3>
        <p className="text-xs text-ink-muted mb-4">
          Capabilities verified cryptographically in backend JWT <code className="font-mono text-brand-600">app_metadata.role</code> claim.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-canvas border-b border-surface-border text-ink-muted uppercase font-semibold text-[10px]">
              <tr>
                <th className="py-2.5 px-3">System Capability</th>
                <th className="py-2.5 px-3 text-center">Admin</th>
                <th className="py-2.5 px-3 text-center">Fraud Investigator</th>
                <th className="py-2.5 px-3 text-center">Customer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {permissions.map((p, i) => (
                <tr key={i} className="hover:bg-surface-subtle">
                  <td className="py-2.5 px-3 font-medium text-ink">{p.capability}</td>
                  <td className="py-2.5 px-3 text-center">
                    {p.admin ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 mx-auto" />
                    ) : (
                      <XCircle className="h-4 w-4 text-slate-300 mx-auto" />
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {p.investigator ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 mx-auto" />
                    ) : (
                      <XCircle className="h-4 w-4 text-slate-300 mx-auto" />
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {p.customer ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 mx-auto" />
                    ) : (
                      <XCircle className="h-4 w-4 text-slate-300 mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Admin Audit Log Section */}
      <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-bold text-ink">Administrative Security Audit Trail</h3>
            <p className="text-xs text-ink-muted">Live events queried from <code className="font-mono text-brand-600">/api/v1/admin/audit-logs</code></p>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface-subtle border border-surface-border text-ink-secondary">
            Role requirement: admin
          </span>
        </div>

        {isAdmin ? (
          <div className="space-y-2">
            {auditLogs.length > 0 ? (
              auditLogs.map((log, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-surface-border bg-canvas text-xs flex justify-between items-center">
                  <div>
                    <span className="font-bold text-ink block">{log.action || 'SECURITY_EVENT'}</span>
                    <span className="text-[11px] text-ink-muted">{log.details || JSON.stringify(log)}</span>
                  </div>
                  <span className="font-mono text-[10px] text-ink-muted">{log.timestamp || 'Live'}</span>
                </div>
              ))
            ) : (
              <div className="p-4 rounded-lg bg-canvas text-center text-xs text-ink-muted border border-surface-border">
                {isLoadingLogs ? 'Fetching verified audit logs...' : 'Zero recent administrative security violations logged.'}
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 rounded-lg bg-surface-subtle border border-surface-border text-center text-xs text-ink-muted">
            Audit logs hidden. Authenticate with Administrator credentials to view privileged access records.
          </div>
        )}
      </div>
    </AppShell>
  )
}
